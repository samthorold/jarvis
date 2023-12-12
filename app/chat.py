import json
from pathlib import Path
from typing import Self

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam as ChatMsg
from pydantic import BaseModel


system_msg: ChatMsg = {
    "role": "system",
    "content": (
        "You are a helpful assistant"
        # " who gives answers in a format consistent with GitHub flavour markdown. "
        # "Do not tell me the answer is consistent with GitHub flavour markdown and "
        # "do not include the ``` fences."
    ),
}


class Chat(BaseModel):
    client: OpenAI
    model: str = "gpt-4-1106-preview"
    messages: list[ChatMsg] = [system_msg]
    completion_tokens: int = 0
    prompt_tokens: int = 0

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_file(cls, path: Path | str, client: OpenAI | None = None) -> Self:
        print(path)
        client = OpenAI() if client is None else client
        with open(path) as f:
            kwargs = json.load(f)
        return cls.model_validate(kwargs | {"client": client})

    def to_json(self) -> str:
        return self.model_dump_json(exclude={"client"})

    def to_file(self, path: Path | str) -> None:
        print(path)
        with open(path, "w") as f:
            f.write(self.to_json())

    def chat(self, msg: str) -> str:
        user_msg: ChatMsg = {"role": "user", "content": msg}
        self.messages.append(user_msg)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )
        content = response.choices[0].message.content or ""
        assistant_msg: ChatMsg = {"role": "assistant", "content": content}
        self.messages.append(assistant_msg)
        self.completion_tokens += (
            0 if response.usage is None else response.usage.completion_tokens
        )
        self.prompt_tokens += (
            0 if response.usage is None else response.usage.prompt_tokens
        )

        return content


if __name__ == "__main__":
    chat = Chat(client=OpenAI())
    while True:
        msg = input("Qu: ")
        if msg in ["q", "Q"]:
            break
        print(chat.chat(msg))
        print()
