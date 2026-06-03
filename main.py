import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
from dotenv import load_dotenv

# Carrega variáveis do .env (se existir)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
# URL base para instâncias Mobile conforme documentação do Postman
ZAPI_MOBILE_URL = "https://api.z-api.io/instances/mobile"


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

# Armazena estado da ativação (apenas para memória de execução)
pending_activations = {}


class RequestAtivacao(BaseModel):
    numero_master: str


class RequestValidacao(BaseModel):
    numero_master: str
    codigo_sms: str


@app.post("/iniciar-ativacao")
async def iniciar_ativacao(req: RequestAtivacao):
    if not ZAPI_CLIENT_TOKEN:
        raise HTTPException(status_code=500, detail="Token não configurado.")

    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    try:
        # Passo 1: Registro do dispositivo (Mobile)
        resp = await app.state.http_client.post(
            f"{ZAPI_MOBILE_URL}/register",
            headers=headers,
            json={"phone": req.numero_master}
        )
        resp.raise_for_status()
        data = resp.json()

        logger.info(f"Registro Z-API: {data}")

        # Ajuste esta chave se a Z-API retornar algo diferente de 'instanceId'
        pending_activations[req.numero_master] = req.numero_master
        return {"status": "SMS solicitado com sucesso."}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro registro: {e.response.text}")
        raise HTTPException(status_code=400, detail="Erro ao registrar telefone.")


@app.post("/finalizar-ativacao")
async def finalizar_ativacao(req: RequestValidacao):
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    try:
        # Passo 2: Validação do código PIN
        resp = await app.state.http_client.post(
            f"{ZAPI_MOBILE_URL}/code",
            headers=headers,
            json={"phone": req.numero_master, "code": req.codigo_sms}
        )

        if resp.status_code == 200:
            token = resp.json().get('token')
            return {"status": "Ativação concluída", "token": token}

        raise HTTPException(status_code=400, detail="Código inválido.")
    except Exception as e:
        logger.error(f"Erro validação: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro no servidor.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)