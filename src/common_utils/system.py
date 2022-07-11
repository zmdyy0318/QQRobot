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
            logger.error("json_str_to_list error, e:{}", e)
            return False, None

    @classmethod
    def dict_to_json_str(cls, dict_val: dict) -> str:
        return json.dumps(dict_val)

    @classmethod
    def json_str_to_dict(cls, json_str: str) -> (bool, dict):
        try:
            return True, json.loads(json_str)
        except (Exception,) as e:
            logger.error("json_str_to_dict error, e:{}", e)
            return False, None


async def is_plugin_enable(event: Event, core_db: Database, plugin_name: str, default: bool = True) -> bool:
    success, enable_val = core_db.get_value(plugin_name, "enable")
    if success is False:
        return default
    if enable_val == 0:
        return False

    if not hasattr(event, "group_id"):
        return True

    sender_group = event.group_id

    success, enable_list_val = core_db.get_value(plugin_name, "group_id_list")
    if success is False:
        return default
    if enable_list_val is None:
        return default

    ret, enable_list = JsonUtil.json_str_to_list(enable_list_val)
    if ret is False:
        return default

    if len(enable_list) == 0:
        return True

    for group_id in enable_list:
        if group_id == sender_group:
            return True

    return False


async def get_enable_group(core_db: Database, plugin_name: str) -> list:
    default = []
    success, enable_val = core_db.get_value(plugin_name, "enable")
    if success is False:
        return default
    if enable_val == 0:
        return default

    success, enable_list_val = core_db.get_value(plugin_name, "group_id_list")
    if success is False:
        return default
    if enable_list_val is None:
        return default

    ret, enable_list = JsonUtil.json_str_to_list(enable_list_val)
    if ret is False:
        return default

    return enable_list
