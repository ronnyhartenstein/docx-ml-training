import json
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from training_data.prompt_templates import INFERENCE_SYSTEM_PROMPT

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]


def _build_messages(request: ChatRequest) -> list[dict]:
    messages = [{"role": "system", "content": INFERENCE_SYSTEM_PROMPT}]
    for entry in request.history[-10:]:   # letzte 10 Nachrichten als Kontext
        if entry.get("role") in ("user", "assistant"):
            messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": request.message})
    return messages


async def _stream_from_mlx(messages: list[dict]) -> AsyncGenerator[str, None]:
    url = f"{settings.mlx_server_url}/v1/chat/completions"
    payload = {
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise HTTPException(
                        status_code=502,
                        detail=f"MLX-Server Fehler {response.status_code}: {body.decode()}",
                    )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError):
                        continue
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="MLX-Server nicht erreichbar. Bitte 'bash scripts/5_serve.sh' ausführen.",
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    messages = _build_messages(request)

    async def sse_generator():
        async for token in _stream_from_mlx(messages):
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat")
async def chat(request: ChatRequest):
    """Nicht-streaming Endpunkt (sammelt vollständige Antwort)."""
    messages = _build_messages(request)
    full_response = ""
    async for token in _stream_from_mlx(messages):
        full_response += token
    return {"response": full_response}
