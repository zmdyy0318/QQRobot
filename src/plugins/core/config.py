from pydantic import BaseSettings


class Config(BaseSettings):
    plugin_names: list
    superusers: list

    class Config:
        extra = "ignore"
