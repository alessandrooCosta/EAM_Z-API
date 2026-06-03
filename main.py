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

pending_activations = {}


class RequestAtivacao(BaseModel):
    numero_master: str


class RequestValidacao(BaseModel):
    numero_master: str
    codigo_sms: str


@app.post("/iniciar-ativacao")
async def iniciar_ativacao(req: RequestAtivacao):
    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    # PASSO 1: Criar a instância para obter o ID e o Token iniciais
    try:
        resp_inst = await app.state.http_client.post(
            f"{ZAPI_BASE_URL}",
            headers=headers,
            json={"phone": req.numero_master}
        )
        resp_inst.raise_for_status()
        data_inst = resp_inst.json()
        instance_id = data_inst.get("instanceId")
        instance_token = data_inst.get("token")

        # PASSO 2: Registrar o dispositivo usando a URL com ID e Token
        url_register = f"{ZAPI_BASE_URL}/{instance_id}/token/{instance_token}/mobile/register-device"
        resp_reg = await app.state.http_client.post(url_register, headers=headers)
        resp_reg.raise_for_status()

        pending_activations[req.numero_master] = {"id": instance_id, "token": instance_token}
        return {"status": "SMS solicitado com sucesso."}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro na Z-API: {e.response.text}")
        raise HTTPException(status_code=400, detail=f"Erro na Z-API: {e.response.text}")


@app.post("/iniciar-ativacao")
async def iniciar_ativacao(req: RequestAtivacao):
    # Usando seus dados fixos
    instance_id = "3F3FFF935EDF520CE87FFADA20428719"
    instance_token = "AB285FC72F855484BB843AB0"

    headers = {"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"}

    # Tentativa de Registro (Verificando se é GET ou POST)
    url_register = f"{ZAPI_BASE_URL}/{instance_id}/token/{instance_token}/mobile/register-device"

    try:
        # A maioria das APIs Z-API Mobile aceita POST aqui.
        # Se der 405 novamente, troque para 'await app.state.http_client.get'
        resp = await app.state.http_client.post(
            url_register,
            headers=headers,
            json={"phone": req.numero_master}
        )

        if resp.status_code == 405:
            # Tenta GET caso o POST falhe com 405
            resp = await app.state.http_client.get(url_register, headers=headers)

        resp.raise_for_status()

        pending_activations[req.numero_master] = {"id": instance_id, "token": instance_token}
        return {"status": "Registro enviado. Verifique o SMS."}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro no registro: {e.response.text}")
        raise HTTPException(status_code=400, detail=f"Erro: {e.response.text}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)