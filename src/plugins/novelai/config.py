from pydantic import BaseSettings


class Config(BaseSettings):
    ali_access_id: str
    ali_access_key: str
    ali_region_hz: str
    ali_region_sh: str
    nai_username: str
    nai_password: str

    class Config:
        extra = "ignore"
