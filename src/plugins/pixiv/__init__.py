import nonebot
from nonebot import require
from nonebot import get_driver
from nonebot.log import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config
from .pixiv import Pixiv

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "pixiv"
plugin_keyword = "来点"
if global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword

data_base_col = {
    "mode": "text",
    "last_time": "int",
}
pixiv_db = Database()
if not pixiv_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init genshin table error")
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(config)
bean_container.register(pixiv_db)

module_list = [
    Pixiv(bean_container, plugin_keyword, "来点什么?例如:\n来点班尼特(普通)/来点涩图(随机涩图)/来点班尼特涩图(指定涩图)"),
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

pixiv = on_message(priority=10, rule=check_enable)


@pixiv.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await pixiv.finish(message)
