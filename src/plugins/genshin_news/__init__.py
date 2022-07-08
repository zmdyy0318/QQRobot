from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import Event
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, is_plugin_enable, get_enable_group
from .fetch_news import FetchNews

require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "genshin_news"
plugin_keyword = "原神订阅"
if global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword

data_base_col = {
    "types": "text",
    "post_ids": "text",
}
genshin_news_db = Database()
if not genshin_news_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init genshin_news table error")
bean_container = BeanContainer()
bean_container.register(genshin_news_db)
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")

module_list = [
    FetchNews("获取公告", "获取最新公告", bean_container),
    FetchNews("获取活动", "获取最新活动", bean_container),
    FetchNews("获取资讯", "获取最新资讯", bean_container),
]

genshin_news = on_startswith(plugin_keyword)


@genshin_news.handle()
async def handle(event: Event):
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return
    sender_id = int(event.get_user_id())
    text = event.get_plaintext()
    text = text.lstrip(plugin_keyword).strip()
    if len(text) == 0:
        message = "指令格式：\n"
        for module in module_list:
            message += f"{plugin_keyword}{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await genshin_news.finish(message)

    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle(sender_id, module.strip_keyword(text))
            if message is not None:
                await genshin_news.finish(message)


@scheduler.scheduled_job("interval", seconds=60*10)
async def task():
    groups = await get_enable_group(core_db, plugin_name)
    for module in module_list:
        await module.task(groups)

