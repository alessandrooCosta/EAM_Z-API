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

# Configurações fixas conforme solicitado
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
INSTANCE_ID = "3F427F76F29322EADCBA7AE31EDEB32B"
INSTANCE_TOKEN = "03BA98B531E87A53E5328605"
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
    url_code = f"{BASE_URL}/phone-code/{req.numero_master}"

    try:
        resp = await app.state.http_client.get(url_code, headers=headers)
        resp.raise_for_status()
        logger.info(f"SMS solicitado para: {req.numero_master}")
        data = resp.json()
        return {"status": "Código SMS solicitado com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao solicitar SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/finalizar-ativacao")
async def finalizar_ativacao(req: RequestValidacao):
    # Endpoint para confirmar o PIN enviado por SMS
    url = f"{BASE_URL}/mobile/confirm-pin-code"

    try:
        resp = await app.state.http_client.post(
            url,
            headers={"Client-Token": ZAPI_CLIENT_TOKEN, "Content-Type": "application/json"},
            json={"code": req.codigo_sms}
        )

        if resp.status_code == 200:
            return {"status": "Ativação concluída", "response": resp.json()}

        raise HTTPException(status_code=400, detail="Código PIN inválido ou erro na Z-API.")
    except Exception as e:
        logger.error(f"Erro na validação: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)