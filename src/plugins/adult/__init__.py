from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Event

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, is_plugin_enable
from src.common_utils.aliyun import Green
from .image import Image

require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "adult"

core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")
green = Green(config.ali_access_id, config.ali_access_key, config.ali_region_sh)
bean_container = BeanContainer()
bean_container.register(green)

module_image = Image(bean_container)

adult = on_message(priority=10)


@adult.handle()
async def handle(event: Event):
    url_list = []
    for seg in event.get_message():
        if seg.type == "image":
            url_list.append(seg.data["url"])
    if len(url_list) == 0:
        return
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return
    handle_ret, score = await module_image.handle(url_list)
    if handle_ret is False or score < 0.5:
        return

    count = round(score / 20.0) + 1
    await adult.send("💦" * count)

