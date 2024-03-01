import enum
from typing import List
from . import util
from openai import OpenAI
import logging

api_key = util.get_env_var("OPENAI_API_KEY", must_exist=True)
client = OpenAI(api_key=api_key)

# https://platform.openai.com/docs/api-reference/chat/object


class Role(str, enum.Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class ChatMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content

    def __str__(self):
        return f"ChatMessage(role={self.role}, content={self.content})"


def chat_gpt(messages: List[ChatMessage], temperature=0.3, max_tokens=256):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        msg = completion.choices[0].message
        return ChatMessage(role=Role.ASSISTANT, content=msg.content)
    except Exception as e:
        logging.error(e)
        return None
