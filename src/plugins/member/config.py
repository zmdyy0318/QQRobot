from pydantic import BaseSettings


class Config(BaseSettings):
    member_admin_groups: list

    class Config:
        extra = "ignore"
