from pydantic import BaseSettings


class Config(BaseSettings):
    proxy_host: str
    proxy_port: str
    ali_access_id: str
    ali_access_key: str
    ali_region_hz: str

    class Config:
        extra = "ignore"
