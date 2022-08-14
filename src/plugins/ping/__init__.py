import nonebot
from nonebot import require
from nonebot import get_driver
from nonebot.log import logger
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .config import Config
from .ping import Ping

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, get_enable_group


require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "ping"
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")
bean_container = BeanContainer()
bean_container.register(config)

module_ping = Ping(bean_container)


@scheduler.scheduled_job("interval", seconds=60*60)
async def task():
    groups = await get_enable_group(core_db, plugin_name)
    if len(groups) == 0:
        return

    message = "ping"
    message += await module_ping.ping_proxy()

    bot = nonebot.get_bot()
    for group in groups:
        try:
            await bot.send_group_msg(group_id=group, message=message)
        except Exception as e:
            logger.error(f"send ping msg error, e:{e}")
            continue

