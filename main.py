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

# Configurações fixas para teste
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
INSTANCE_ID = "3F3FFF935EDF520CE87FFADA20428719"
INSTANCE_TOKEN = "AB285FC72F855484BB843AB0"
BASE_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{INSTANCE_TOKEN}"


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
        # 1. Verificar disponibilidade
        await app.state.http_client.post(
            f"{BASE_URL}/mobile/register/check-availability",
            headers=headers,
            json={"phone": req.numero_master}
        )

        # 2. Solicitar código de confirmação (SMS)
        resp = await app.state.http_client.post(
            f"{BASE_URL}/mobile/register/request-code",
            headers=headers,
            json={"phone": req.numero_master}
        )

        resp.raise_for_status()
        logger.info(f"SMS solicitado para: {req.numero_master}")
        return {"status": "Código SMS solicitado com sucesso."}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro na Z-API: {e.response.text}")
        raise HTTPException(status_code=400, detail=f"Erro no fluxo de registro: {e.response.text}")


@app.post("/finalizar-ativacao")
async def finalizar_ativacao(req: RequestValidacao):
    # 3. Confirmar código recebido por SMS
    url = f"{BASE_URL}/mobile/register/confirm-code"

    try:
        resp = await app.state.http_client.post(
            url,
            headers={"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"},
            json={"phone": req.numero_master, "code": req.codigo_sms}
        )

        if resp.status_code == 200:
            return {"status": "Ativação concluída", "response": resp.json()}

        raise HTTPException(status_code=400, detail="Código PIN inválido ou expirado.")
    except Exception as e:
        logger.error(f"Erro na validação: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)