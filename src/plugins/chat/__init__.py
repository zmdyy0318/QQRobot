from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, is_plugin_enable
from .chatter import Chatter

require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "chat"

data_base_col = {

}
chat_db = Database()
if not chat_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init chat_db table error")
bean_container = BeanContainer()
bean_container.register(chat_db)
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")
bean_container.register(config)
module_chatter = Chatter(bean_container)

chat = on_message(priority=10)


@chat.handle()
async def handle(event: Event):
    text = ""
    for seg in event.get_message():
        if seg.type == "text":
            text += seg.data["text"]
        else:
            return
    if len(text) == 0:
        return
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return

    if not isinstance(event, GroupMessageEvent):
        return

    ret, reply_text = await module_chatter.handle(event.group_id, text)
    if ret is False or len(reply_text) == 0:
        return
    await chat.send(reply_text)


