from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config

from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import Green
from .image import Image
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "adult"

global_core = GlobalCore()
green = Green(config.ali_access_id, config.ali_access_key, config.ali_region_sh)

bean_container = BeanContainer()
bean_container.register(green)
bean_container.register(config)

module_image = Image(bean_container)


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

adult = on_message(priority=10, rule=check_enable)


@adult.handle()
async def handle(event: GroupMessageEvent):
    message = await module_image.handle_event(event)
    if message is not None:
        await adult.finish(message)

