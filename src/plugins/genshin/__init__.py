from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
from .sign_reward import SignReward
from .bind_account import BindAccount
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "genshin"
plugin_keyword = "原神"
if global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword

data_base_col = {
    "cookie": "text",
}
genshin_db = Database()
if not genshin_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init genshin table error")
global_core = GlobalCore()

bean_container = BeanContainer()
bean_container.register(genshin_db)

module_list = [
    BindAccount(bean_container, plugin_keyword + "绑定", "绑定米游社账号"),
    SignReward(bean_container, plugin_keyword + "签到", "米游社每日签到"),
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

genshin = on_startswith(plugin_keyword, priority=1, rule=check_enable)


@genshin.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    if text == plugin_keyword:
        message = "指令格式：\n"
        for module in module_list:
            message += f"{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await genshin.finish(message)

    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await genshin.finish(message)

