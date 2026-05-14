from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhooks/hubla")
async def hubla_webhook(request: Request):
    # Stub — implementação completa na sprint de webhooks
    return {"status": "ok"}
