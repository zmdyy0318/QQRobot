from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
from .fetch_news import FetchNews
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "genshin_news"
plugin_keyword_ys = "原神订阅"
plugin_keyword_sr = "星铁订阅"
if hasattr(global_config, "environment") and global_config.environment == "dev":
    plugin_keyword_ys = "/" + plugin_keyword_ys
    plugin_keyword_sr = "/" + plugin_keyword_sr

data_base_col = {
    "types": "text",
    "post_ids": "text",
    "gids": "text",
}
genshin_news_db = Database()
if not genshin_news_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init genshin_news table error")
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(genshin_news_db)

module_list_ys = [
    FetchNews(bean_container, plugin_keyword_ys + "获取公告", "获取原神最新公告"),
    FetchNews(bean_container, plugin_keyword_ys + "获取活动", "获取原神最新活动"),
    FetchNews(bean_container, plugin_keyword_ys + "获取资讯", "获取原神最新资讯"),
]

module_list_sr = [
    FetchNews(bean_container, plugin_keyword_sr + "获取公告", "获取铁道最新公告"),
    FetchNews(bean_container, plugin_keyword_sr + "获取活动", "获取铁道最新活动"),
    FetchNews(bean_container, plugin_keyword_sr + "获取资讯", "获取铁道最新资讯"),
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

genshin_news_ys = on_startswith(plugin_keyword_ys, priority=1, rule=check_enable)
genshin_news_sr = on_startswith(plugin_keyword_sr, priority=1, rule=check_enable)


@genshin_news_ys.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    if text == plugin_keyword_ys:
        message = "指令格式：\n"
        for module in module_list_ys:
            message += f"{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await genshin_news_ys.finish(message)

    for module in module_list_ys:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await genshin_news_ys.finish(message)


@genshin_news_sr.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    if text == plugin_keyword_sr:
        message = "指令格式：\n"
        for module in module_list_sr:
            message += f"{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await genshin_news_sr.finish(message)

    for module in module_list_sr:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await genshin_news_sr.finish(message)


@scheduler.scheduled_job("interval", seconds=60*10)
async def task():
    groups = global_core.get_enable_group(plugin_name)
    if len(groups) == 0:
        return
    for module in module_list_ys:
        await module.task(groups)
    for module in module_list_sr:
        await module.task(groups)

