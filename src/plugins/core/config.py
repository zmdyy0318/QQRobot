from pydantic import BaseSettings


class Config(BaseSettings):
    plugin_names: list
    superusers: list
    onebot_ws_urls: list
    onebot_access_token: str

    class Config:
        extra = "ignore"
