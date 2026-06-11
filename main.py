import os
import uvicorn
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# Configurações fixas que você definiu
CONFIG = {
    "USER": "ACOSTA",
    "ORGANIZATION": "ASSET-TEST",
    "EQUIPMENT_CODE": "AMI-0001",
    "REQUEST_TYPE": "BRKD",
    "TENANT": "IBNQI1720580460_DEM",
    "API_KEY": "afa01ac01d-de5a-4732-9fbc-0417178a7d73",
    "BASE_URL": "https://us1.eam.hxgnsmartcloud.com/axis/restservices"
}


async def abrir_os_no_eam(descricao_msg):
    url = f"{CONFIG['BASE_URL']}/workorders"
    headers = {
        "tenant": CONFIG['TENANT'],
        "x-api-key": CONFIG['API_KEY'],
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    # Payload estruturado conforme suas exigências:
    # Mantemos a hierarquia necessária, mas sem passar listas vazias
    # Payload com o campo Departamento incluído
    payload = {
        "WORKORDERID": {
            "DESCRIPTION": descricao_msg,
            "ORGANIZATIONID": {"ORGANIZATIONCODE": CONFIG['ORGANIZATION']}
        },
        "EQUIPMENTID": {
            "EQUIPMENTCODE": CONFIG['EQUIPMENT_CODE'],
            "ORGANIZATIONID": {"ORGANIZATIONCODE": CONFIG['ORGANIZATION']}
        },
        "TYPE": {
            "TYPECODE": CONFIG['REQUEST_TYPE']
        },
        "STATUS": {
            "STATUSCODE": "R"
        },
        "DEPARTMENTID": {
            "DEPARTMENTCODE": "*"  # O asterisco geralmente representa o departamento padrão do usuário
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()

@app.post("/webhook")
async def webhook_whatsapp(request: Request):
    data = await request.json()
    mensagem = data.get("message", {}).get("text", "")

    if mensagem:
        resultado = await abrir_os_no_eam(mensagem)
        print(f"EAM Response: {resultado}")
        return {"status": "success", "eam_response": resultado}

    return {"status": "error", "message": "Mensagem vazia"}

if __name__ == "__main__":
    # O Render espera que a porta seja definida via variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)