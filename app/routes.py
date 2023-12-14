import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Form, Request, Response, WebSocket, WebSocketDisconnect
from markdown2 import markdown  # pyright: ignore
from openai import OpenAI

from app.config import Settings
from app.chat import Chat


settings = Settings()

router = APIRouter()


JARVIS_COOKIE_NAME = "Jarvis-session"
CHAT_DIR = Path("chats")
if not CHAT_DIR.exists():
    CHAT_DIR.mkdir()


with open(settings.TEMPLATE_DIR / "base.html") as f:
    HTML = f.read()


with open(settings.TEMPLATE_DIR / "interaction.html") as f:
    INTERACTION = f.read()


@router.get("/")
def index(response: Response):
    session = uuid4().hex
    print(f"New session: {session}")
    response.set_cookie(key=JARVIS_COOKIE_NAME, value=session)
    return HTML


@router.post("/message")
def message(request: Request, question: Annotated[str, Form()]):
    session = request.cookies.get(JARVIS_COOKIE_NAME)
    print(session)
    if session is None:
        chat = Chat(client=OpenAI())
        answer = chat.chat(question)
    else:
        path = CHAT_DIR / session
        if not path.exists():
            chat = Chat(client=OpenAI())
        else:
            chat = Chat.from_file(path)
        answer = chat.chat(question)
        chat.to_file(path)

    return INTERACTION.format(
        question=markdown(
            question, extras=["fenced-code-blocks"]
        ),  # pyright: ignore[reportUnknownArgumentType]
        answer=markdown(
            answer, extras=["fenced-code-blocks"]
        ),  # pyright: ignore[reportUnknownArgumentType]
    )


@router.websocket("/stream")
async def stream(ws: WebSocket):
    chat = Chat(client=OpenAI())
    await ws.accept()
    try:
        while True:
            text = await ws.receive_json()
            qu = text.get("question")
            if not qu:
                raise RuntimeError("Something has gone wrong here. No 'question' key.")
            qu_html = markdown(qu, extras=["fenced-code-blocks"])  # pyright: ignore
            await asyncio.sleep(0)
            await ws.send_text(
                '<div id="chat" hx-swap-oob="beforeend">'
                f'<div class="user-msg">{qu_html}</div></div>'
            )
            await asyncio.sleep(0)
            await ws.send_text(
                '<input id="question" name="question" type="text" class="form-control"'
                ' placeholder="Chat to Jarvis ..." hx-swap-oob="true"></input>'
            )
            await asyncio.sleep(0)
            cumulative_tokens = tokens_html = ""
            async for tk in chat.stream(qu):
                cumulative_tokens += tk
                tokens_html = markdown(  # pyright: ignore
                    cumulative_tokens,
                    extras=["fenced-code-blocks"],
                )
                await asyncio.sleep(0)
                await ws.send_text(
                    '<div id="tokens" hx-swap-oob="true">'
                    f'<div class="assistant-msg">{tokens_html}</div></div>'
                )
            await asyncio.sleep(0)
            await ws.send_text(
                '<div id="chat" hx-swap-oob="beforeend">'
                f'<div class="assistant-msg">{tokens_html}</div></div>'
            )
            await asyncio.sleep(0)
            await ws.send_text(f'<div id="tokens" hx-swap-oob="true"></div>')
    except WebSocketDisconnect:
        print("Disconnected.")
