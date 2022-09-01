from nonebot import require
from nonebot import get_driver
from nonebot import on_message, on_endswith
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from src.common_utils.database import Database
from .config import Config
from .what import What

from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import NlpNer, NlpPos
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "what"
plugin_keyword = "什么"
if global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword

data_base_col = {
    "tag": "text",
    "word": "text",
}
what_db = Database()
if not what_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init genshin_news table error")
nlp_ner = NlpNer(config.ali_access_id, config.ali_access_key, config.ali_region_hz)
nlp_pos = NlpPos(config.ali_access_id, config.ali_access_key, config.ali_region_hz)
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(what_db)
bean_container.register(nlp_ner)
bean_container.register(nlp_pos)

module_list = [
    What(bean_container, plugin_keyword, "什么建议")
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

what_keyword = on_endswith(plugin_keyword, priority=1, rule=check_enable)
what_message = on_message(priority=10, rule=check_enable)


@what_keyword.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await what_keyword.finish(message)


@what_message.handle()
async def handle(event: GroupMessageEvent):
    for module in module_list:
        message = await module.handle_event(event)
        if message is not None:
            await what_message.finish(message)


