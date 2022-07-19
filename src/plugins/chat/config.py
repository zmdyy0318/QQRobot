from pydantic import BaseSettings


class Config(BaseSettings):
    maria_host: str
    maria_port: str
    maria_user: str
    maria_password: str
    maria_chat_database: str

    class Config:
        extra = "ignore"
