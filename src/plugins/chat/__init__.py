from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config

from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import Nlp
from .chatter import Chatter
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "chat"

global_core = GlobalCore()
nlp = Nlp(config.ali_access_id, config.ali_access_key, config.ali_region_hz)

bean_container = BeanContainer()
bean_container.register(config)
bean_container.register(nlp)

module_chatter = Chatter(bean_container)


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

chat = on_message(priority=10, rule=check_enable)


@chat.handle()
async def handle(event: GroupMessageEvent):
    message = await module_chatter.handle_event(event)
    if message is not None:
        await chat.finish(message)


