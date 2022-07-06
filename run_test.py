import json
from typing import TYPE_CHECKING, Set

import nonebot
import src.common_utils as common_utils
import asyncio

# def t_database():
#     db = CDatabase()
#     col = {
#         "text1": "text",
#         "text2": "text",
#         "text3": "text",
#         "text4": "text",
#         "text5": "text",
#     }
#     db.init_table(table_name="test", table_key="id", table_col=col)
#     db.is_key_exist(key=123456)
#
#

from pydantic import parse_obj_as
from enum import Enum
from typing import Any, List, Dict, Type, Iterable, Optional, Union


class MessageType(str, Enum):
    """消息类型枚举类"""
    SOURCE = 'Source'
    QUOTE = 'Quote'
    AT = 'At'
    AT_ALL = 'AtAll'
    FACE = 'Face'
    PLAIN = 'Plain'
    IMAGE = 'Image'
    FLASH_IMAGE = 'FlashImage'
    VOICE = 'Voice'
    XML = 'Xml'
    JSON = 'Json'
    APP = 'App'
    DICE = 'Dice'
    POKE = 'Poke'
    MARKET_FACE = 'MarketFace'
    MUSIC_SHARE = 'MusicShare'
    FORWARD_MESSAGE = 'ForwardMessage'
    FILE = 'File'
    MIRAI_CODE = 'MiraiCode'


class MessageSegment(BaseMessageSegment["MessageChain"]):

    type: MessageType
    data: Dict[str, Any]

    @classmethod
    def get_message_class(cls) -> Type["MessageChain"]:
        return MessageChain


async def t_genshin(cookie: str):
    from src.plugins.genshin.api import API

    from src.common_utils.database import Database
    valin = "[{'type': 'Source', 'id': 3507, 'time': 1657075981}, {'type': 'Plain', 'text': 'l'}]"
    value = [parse_obj_as(cls.get_segment_class(), v) for v in valin]

    db = Database()
    a = db.connect_table("genshin")

    ys = API()
    ret, user_role = await ys.init_user_role(cookie)
    if ret is False:
        raise Exception("init user role error")
    ret, sign_info = await ys.get_sign_info()
    if ret is False:
        raise Exception("get sign info error")
    ret, rewards_info = await ys.get_rewards_info()
    if ret is False:
        raise Exception("get rewards info error")
    ret = await ys.act_sign()
    if ret is False:
        raise Exception("act sign error")


if __name__ == "__main__":
    nonebot.init()

    global_config = nonebot.get_driver().config
    genshin_cookie = global_config.test_genshin_cookie
    loop = asyncio.get_event_loop()
    loop.run_until_complete(t_genshin(genshin_cookie))



