from pydantic import BaseSettings


class Config(BaseSettings):
    ali_access_id: str
    ali_access_key: str
    ali_region_sh: str

    class Config:
        extra = "ignore"
