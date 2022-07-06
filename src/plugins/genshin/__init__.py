import json
from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.params import EventPlainText
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent
from nonebot.log import logger
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
from .sign_reward import SignReward
from .bind_account import BindAccount

require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "genshin"

data_base_col = {
    "cookie": "text",
}
genshin_db = Database()
if not genshin_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init genshin table error")
bean_container = BeanContainer()
bean_container.register(genshin_db)
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")

module_list = [
    BindAccount("绑定", "绑定米游社账号", bean_container),
    SignReward("签到", "米游社每日签到", bean_container),
]

genshin = on_startswith("原神")


async def is_plugin_enable(event: Event, default: bool = True) -> bool:
    success, enable_val = core_db.get_value(plugin_name, "enable")
    if success is False:
        return default
    if enable_val == 0:
        return False

    if not isinstance(event, GroupMessageEvent):
        return True

    sender_group = event.group_id

    success, enable_list_val = core_db.get_value(plugin_name, "group_id_list")
    if success is False:
        return default
    if enable_list_val is None:
        return default

    try:
        json_val = json.loads(enable_list_val)
    except (Exception,) as e:
        logger.error("{} is_plugin_enable error, e:{}", plugin_name, e)
        return default

    if len(json_val) == 0:
        return True

    for group_id in json_val:
        if group_id == sender_group:
            return True

    return False


@genshin.handle()
async def handle(event: Event):
    enable = await is_plugin_enable(event)
    if enable is False:
        return
    sender_id = int(event.get_user_id())
    text = event.get_plaintext()
    text = text.lstrip("原神").strip()
    if len(text) == 0:
        message = "指令格式：\n"
        for module in module_list:
            message += f"原神{module.get_keyword()}：{module.get_help()}\n"
        message =  message.rstrip("\n")
        await genshin.finish(message)

    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle(sender_id, module.strip_keyword(text))
            if message is not None:
                await genshin.finish(message)

