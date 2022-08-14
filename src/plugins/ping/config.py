from pydantic import BaseSettings


class Config(BaseSettings):
    proxy_host: str
    proxy_port: str

    class Config:
        extra = "ignore"
