from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import is_plugin_enable


require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "repeat"
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")


class GroupInfo:
    last_message = None
    count = 0

    def __init__(self, last_message, count):
        self.last_message = last_message
        self.count = count


group_map = {}
repeat = on_message(priority=1)


@repeat.handle()
async def handle(event: Event):
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return
    if not isinstance(event, GroupMessageEvent):
        return
    group_id = int(event.group_id)
    if group_id not in group_map:
        group_map[group_id] = GroupInfo(event.message, 1)
        return

    if group_map[group_id].last_message != event.message:
        group_map[group_id].count = 1
        group_map[group_id].last_message = event.message
        return
    group_map[group_id].count += 1

    if group_map[group_id].count == 3:
        await repeat.send(event.message)

