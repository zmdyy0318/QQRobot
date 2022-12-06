from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
from .sixty import Sixty
from .fish import Fish
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "vvhan"
plugin_keyword = "韩小韩"
if hasattr(global_config, "environment") and global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword

data_base_col = {
    "last_60s_flag": "text",
    "last_fish_flag": "text",
}
han_db = Database()
if not han_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init han_db table error")
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(han_db)
bean_container.register(config)

module_list = [
    Sixty(bean_container, plugin_keyword + "新闻", "获取60秒新闻"),
    Fish(bean_container, plugin_keyword + "摸鱼", "获取60秒新闻"),
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

han = on_startswith(plugin_keyword, priority=1, rule=check_enable)


@han.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    if text == plugin_keyword:
        message = "指令格式：\n"
        for module in module_list:
            message += f"{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await han.finish(message)

    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await han.finish(message)


@scheduler.scheduled_job("interval", seconds=60 * 10)
async def task():
    groups = global_core.get_enable_group(plugin_name)
    if len(groups) == 0:
        return
    for module in module_list:
        await module.task(groups)

