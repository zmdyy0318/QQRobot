from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .config import Config

from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import Green
from src.common_utils.database import Database
from .gpt import ChatGPT
require('core')
from src.plugins.core.core import GlobalCore

data_base_col = {
    "session_token": "text",
    "authorization": "text",
    "refresh_time": "int",
}
global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "openai"
repeat_db = Database()
if not repeat_db.init_table(table_name=plugin_name, table_key="global", table_key_type=str, table_col=data_base_col):
    raise Exception("init repeat table error")

global_core = GlobalCore()
bean_container = BeanContainer()
bean_container.register(repeat_db)
bean_container.register(config)

module_gpt = ChatGPT(bean_container)


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

adult = on_message(priority=10, rule=check_enable)


@adult.handle()
async def handle(event: GroupMessageEvent):
    message = await module_gpt.handle_event(event)
    if message is not None:
        await adult.finish(message)


@scheduler.scheduled_job("interval", seconds=60 * 30)
async def task():
    groups = global_core.get_enable_group(plugin_name)
    if len(groups) == 0:
        return
    await module_gpt.task(groups)
