from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Form, Request, Response
from jinja2_fragments.fastapi import Jinja2Blocks
from markdown2 import (  # pyright: ignore[reportMissingTypeStubs]
    markdown,  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]
)
from openai import OpenAI

from app.config import Settings
from app.chat import Chat


settings = Settings()

templates = Jinja2Blocks(settings.TEMPLATE_DIR)
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
