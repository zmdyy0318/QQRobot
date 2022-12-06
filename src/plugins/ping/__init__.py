from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .config import Config
from .ping import Ping

from src.common_utils.system import BeanContainer
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "ping"
plugin_keyword = "ping"
if hasattr(global_config, "environment") and global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(config)

module_list = [
    Ping(bean_container, plugin_keyword, "获取服务器状态")
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

ping = on_startswith(plugin_keyword, priority=1, rule=check_enable)


@ping.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await ping.finish(message)


@scheduler.scheduled_job("interval", seconds=60*60)
async def task():
    groups = global_core.get_enable_group(plugin_name)
    if len(groups) == 0:
        return
    for module in module_list:
        await module.task(groups)

