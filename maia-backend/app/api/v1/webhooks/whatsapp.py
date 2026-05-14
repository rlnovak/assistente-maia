from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    # Stub — implementação na sprint de WhatsApp (Sprint 10)
    return {"status": "ok"}
