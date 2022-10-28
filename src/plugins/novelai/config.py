from pydantic import BaseSettings


class Config(BaseSettings):
    ali_access_id: str
    ali_access_key: str
    ali_region_hz: str
    ali_region_sh: str
    ali_oss_bucket_name: str
    ali_oss_bucket_url: str
    nai_username: str
    nai_password: str
    proxy_host: str
    proxy_port: str

    class Config:
        extra = "ignore"
