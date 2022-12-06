from pydantic import BaseSettings


class Config(BaseSettings):
    openai_session_token: str

    class Config:
        extra = "ignore"
