"""AI Weather & Hazard Assistant API Route."""
import logging
from fastapi import APIRouter, HTTPException

from backend.app.models.schema import AssistantChatRequest, AssistantChatResponse
from backend.app.services.assistant_service import generate_assistant_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/assistant/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(payload: AssistantChatRequest):
    """Grounded AI Weather & Hazard Assistant endpoint across 788 LGD districts."""
    try:
        result = await generate_assistant_response(
            message=payload.message,
            current_location=payload.current_location,
            history=payload.history,
        )
        return AssistantChatResponse(
            reply=result["reply"],
            sources=result["sources"],
            tools_used=result["tools_used"],
            timestamp_ist=result["timestamp_ist"],
            context_location=result.get("context_location"),
            advisory=result["advisory"],
        )
    except Exception as ex:
        logger.exception("Assistant chat endpoint error: %s", ex)
        raise HTTPException(status_code=500, detail=f"Assistant processing error: {str(ex)}")
