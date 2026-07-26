from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["public"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "shared-chatgpt-memory", "version": "1.0.0"}


@router.get("/privacy", response_class=PlainTextResponse)
async def privacy(request: Request) -> str:
    contact = request.app.state.settings.contact_email or "the service owner"
    return (
        "Shared Memory privacy notice\n\n"
        "This service processes explicitly requested, non-sensitive shared memory "
        "through Mem0. All authorized users share "
        "one vault. Do not submit secrets, payment, health, or confidential data.\n\n"
        f"Contact: {contact}\n"
    )
