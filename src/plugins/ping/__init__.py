import nonebot
from nonebot import require
from nonebot import get_driver
from nonebot.log import logger
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import get_enable_group


require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "ping"
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")


@scheduler.scheduled_job("interval", seconds=60*60)
async def task():
    groups = await get_enable_group(core_db, plugin_name)
    bot = nonebot.get_bot()
    for group in groups:
        try:
            await bot.send_group_msg(group_id=group, message="ping")
        except Exception as e:
            logger.error(f"send ping msg error, e:{e}")
            continue

