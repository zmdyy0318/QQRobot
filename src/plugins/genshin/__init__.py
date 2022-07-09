from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import Event
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, is_plugin_enable
from .sign_reward import SignReward
from .bind_account import BindAccount

require('core')

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
bean_container = BeanContainer()
bean_container.register(genshin_db)
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")

module_list = [
    BindAccount("绑定", "绑定米游社账号", bean_container),
    SignReward("签到", "米游社每日签到", bean_container),
]

genshin = on_startswith(plugin_keyword, priority=10)


@genshin.handle()
async def handle(event: Event):
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return
    sender_id = int(event.get_user_id())
    text = event.get_plaintext()
    text = text.lstrip(plugin_keyword).strip()
    if len(text) == 0:
        message = "指令格式：\n"
        for module in module_list:
            message += f"{plugin_keyword}{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await genshin.finish(message)

    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle(sender_id, module.strip_keyword(text))
            if message is not None:
                await genshin.finish(message)

