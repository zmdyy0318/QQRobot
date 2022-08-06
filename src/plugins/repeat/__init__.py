from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, is_plugin_enable
from src.common_utils.aliyun import Ocr
from .repeat import Repeat


require('core')


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
bean_container = BeanContainer()
bean_container.register(repeat_db)
bean_container.register(ocr)
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")

module_repeat = Repeat(bean_container)

repeat = on_message(priority=10)


@repeat.handle()
async def handle(event: Event):
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return
    if not isinstance(event, GroupMessageEvent):
        return
    await module_repeat.handle(event)

