from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import ChatReply, ChatRequest
from ..services.chat import answer
from ..services.limits import LimitReachedError, check_chat, client_id

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatReply)
def chat(req: ChatRequest, request: Request):
    if req.messages[-1].role != "user":
        raise HTTPException(422, "The last message must be from the traveller.")
    try:
        check_chat(client_id(request))
    except LimitReachedError as e:
        raise HTTPException(429, str(e)) from None
    return answer(req.messages)
