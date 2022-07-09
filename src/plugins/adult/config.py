from pydantic import BaseSettings


class Config(BaseSettings):
    cts_access_id: str
    cts_access_key: str
    cts_region: str

    class Config:
        extra = "ignore"
