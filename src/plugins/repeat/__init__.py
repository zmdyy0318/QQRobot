from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import Ocr
from .repeat import Repeat
require('core')
from src.plugins.core.core import GlobalCore

data_base_col = {
    "cur_num": "int",
    "next_num": "int",
    "last_time": "int",
}
global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "repeat"
repeat_db = Database()
if not repeat_db.init_table(table_name=plugin_name, table_key="id", table_key_type=str, table_col=data_base_col):
    raise Exception("init repeat table error")
ocr = Ocr(config.ali_access_id, config.ali_access_key, config.ali_region_hz)
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(repeat_db)
bean_container.register(ocr)

module_repeat = Repeat(bean_container)


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

repeat = on_message(priority=10, rule=check_enable)


@repeat.handle()
async def handle(event: GroupMessageEvent):
    message = await module_repeat.handle_event(event)
    if message is not None:
        await repeat.finish(message)

