import json
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent
from .database import Database


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class BeanContainer:
    def __init__(self):
        self.beans = {}

    def register(self, bean):
        self.beans[type(bean)] = bean

    def get_bean(self, c):
        if c in self.beans:
            return self.beans[c]
        else:
            return None


class JsonUtil:
    @classmethod
    def list_to_json_str(cls, list_val: list) -> str:
        return json.dumps(list_val)

    @classmethod
    def json_str_to_list(cls, json_str: str) -> (bool, list):
        try:
            return True, json.loads(json_str)
        except (Exception,) as e:
            logger.error(f"json_str_to_list error, e:{e}")
            return False, None

    @classmethod
    def dict_to_json_str(cls, dict_val: dict) -> str:
        return json.dumps(dict_val)

    @classmethod
    def json_str_to_dict(cls, json_str: str) -> (bool, dict):
        try:
            return True, json.loads(json_str)
        except (Exception,) as e:
            logger.error(f"json_str_to_dict error, e:{e}")
            return False, None

