from nonebot import require
from nonebot import get_driver
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent

from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer, is_plugin_enable
from src.common_utils.aliyun import Nlp
from .chatter import Chatter

require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "chat"

core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")
bean_container = BeanContainer()
bean_container.register(config)

nlp = Nlp()
ret = nlp.init_access_key(config.ali_access_id, config.ali_access_key, config.ali_region_hz)
if ret is False:
    raise Exception("init nlp init_access_key error")
bean_container.register(nlp)

module_chatter = Chatter(bean_container)

chat = on_message(priority=10)


@chat.handle()
async def handle(event: Event):
    text = event.get_plaintext()
    if len(text) == 0 or text.strip() == "":
        return
    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return

    if not isinstance(event, GroupMessageEvent):
        return

    if event.reply is not None \
            and event.reply.sender.user_id == event.self_id \
            and text == "不可以":
        remove_ret = await module_chatter.delete_reply(event.reply.message.extract_plain_text())
        if remove_ret is False:
            await chat.send("我错了下次还敢")
        else:
            await chat.send("我错了")
    else:
        handle_ret, reply_text = await module_chatter.handle(event.group_id, text)
        if handle_ret is False or len(reply_text) == 0:
            return
        await chat.send(reply_text)


