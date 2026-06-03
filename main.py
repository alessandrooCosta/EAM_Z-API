import os
import uvicorn  # Importante: Não esqueça desta importação!
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua "*" pela URL do EAM do seu cliente
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)

# Armazena temporariamente o estado da ativação
pending_activations = {}

class RequestAtivacao(BaseModel):
    numero_master: str

class RequestValidacao(BaseModel):
    numero_master: str
    codigo_sms: str


@app.post("/iniciar-ativacao")
async def iniciar_ativacao(req: RequestAtivacao):

    headers = {
        "Client-Token": "Faf52a7f373cc4792a63d0026a28eb7fdS"
    }

    resp = await client.post(
        "https://api.z-api.io/instances",  # URL base de instâncias
        headers=headers,
        json={"phone": req.numero_master}
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.z-api.io/instances/create-mobile",
            json={"phone": req.numero_master}
        )
        data = resp.json()

        # LOG PARA DEBUG: Isso aparecerá nos logs do Render
        print(f"DEBUG: Resposta completa da Z-API: {data}")

        # Verificação de segurança
        if 'instanceId' in data:
            pending_activations[req.numero_master] = data['instanceId']
            return {"status": "SMS enviado. Aguardando código."}
        else:
            # Se não encontrar, lança um erro amigável para você ver o porquê
            raise HTTPException(
                status_code=500,
                detail=f"Z-API não retornou instanceId. Resposta: {data}"
            )

@app.post("/finalizar-ativacao")
async def finalizar_ativacao(req: RequestValidacao):
    instance_id = pending_activations.get(req.numero_master)

    if not instance_id:
        raise HTTPException(status_code=404, detail="Ativação não iniciada para este número.")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.z-api.io/instances/{instance_id}/validate-code",
            json={"code": req.codigo_sms}
        )

        if resp.status_code == 200:
            token_final = resp.json().get('token')
            # Aqui você pode salvar o token em um banco ou arquivo
            return {"status": "Ativação concluída", "token": token_final}

    raise HTTPException(status_code=400, detail="Código inválido ou erro na ZAPI")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)