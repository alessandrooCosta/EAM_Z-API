import os
import uvicorn
import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
BASE_URL = "https://api.z-api.io/instances"

# --- A VARIÁVEL DEVE FICAR AQUI, FORA DAS FUNÇÕES ---
pending_activations = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestAtivacao(BaseModel):
    numero_master: str


class RequestValidacao(BaseModel):
    numero_master: str
    codigo_sms: str


@app.post("/iniciar-ativacao")
async def iniciar_ativacao(req: RequestAtivacao):
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    try:
        # 1. Cria a instância
        resp = await app.state.http_client.post(
            f"{BASE_URL}",
            headers=headers,
            json={"phone": req.numero_master}
        )
        data = resp.json()
        instance_id = data.get("instanceId")
        instance_token = data.get("token")

        # Armazena globalmente
        pending_activations[req.numero_master] = {"id": instance_id, "token": instance_token}

        # 2. Solicita o código SMS
        url_code = f"{ZAPI_BASE_URL}/{instance_id}/token/{instance_token}/phone-code/{req.numero_master}"
        resp_code = await app.state.http_client.post(url_code, headers=headers)
        resp_code.raise_for_status()

        return {"status": "Instância criada e SMS solicitado."}

    except Exception as e:
        logger.error(f"Erro no fluxo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/finalizar-ativacao")
async def finalizar_ativacao(req: RequestValidacao):
    # Acesso seguro à variável global
    data = pending_activations.get(req.numero_master)
    if not data:
        raise HTTPException(status_code=404, detail="Ativação não iniciada.")

    url = f"{BASE_URL}/{data['id']}/token/{data['token']}/mobile/confirm-pin-code"

    try:
        resp = await app.state.http_client.post(
            url,
            headers={"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"},
            json={"code": req.codigo_sms}
        )
        if resp.status_code == 200:
            pending_activations.pop(req.numero_master, None)
            return {"status": "Ativação concluída", "response": resp.json()}

        raise HTTPException(status_code=400, detail="Código PIN inválido.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)