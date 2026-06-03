import os
import uvicorn
import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
ZAPI_BASE_URL = "https://api.z-api.io/instances"


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

# Dicionário para armazenar temporariamente os dados da instância (ID e TOKEN)
pending_activations = {}


class RequestAtivacao(BaseModel):
    numero_master: str


class RequestValidacao(BaseModel):
    numero_master: str
    codigo_sms: str


@app.post("/iniciar-ativacao")
async def iniciar_ativacao(req: RequestAtivacao):
    if not ZAPI_CLIENT_TOKEN:
        raise HTTPException(status_code=500, detail="Configuração de servidor incompleta.")

    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    try:
        # Endpoint Mobile: Registro do dispositivo
        resp = await app.state.http_client.post(
            f"{ZAPI_BASE_URL}/mobile/register",
            headers=headers,
            json={"phone": req.numero_master}
        )
        resp.raise_for_status()
        data = resp.json()

        logger.info(f"Registro Mobile Z-API: {data}")

        # Salvamos o ID e o Token retornados para usar na validação
        pending_activations[req.numero_master] = {
            "id": data.get("instanceId"),
            "token": data.get("token")
        }

        return {"status": "SMS enviado. Aguardando código."}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro registro Z-API: {e.response.text}")
        raise HTTPException(status_code=400, detail=f"Erro ao registrar telefone: {e.response.text}")


@app.post("/finalizar-ativacao")
async def finalizar_ativacao(req: RequestValidacao):
    # Recupera os dados salvos do passo anterior
    data = pending_activations.get(req.numero_master)
    if not data:
        raise HTTPException(status_code=404, detail="Ativação não iniciada.")

    instance_id = data.get("id")
    instance_token = data.get("token")

    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    try:
        # Endpoint Mobile: Confirmação de PIN (conforme documentação do Postman)
        url = f"{ZAPI_BASE_URL}/{instance_id}/token/{instance_token}/mobile/confirm-pin-code"
        resp = await app.state.http_client.post(
            url,
            headers=headers,
            json={"code": req.codigo_sms}
        )

        if resp.status_code == 200:
            # Removemos da lista de pendentes após sucesso
            pending_activations.pop(req.numero_master, None)
            return {"status": "Ativação concluída", "response": resp.json()}

        raise HTTPException(status_code=400, detail="Código PIN inválido.")
    except Exception as e:
        logger.error(f"Erro na validação: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno na validação.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)