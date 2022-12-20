from nonebot import require
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import Translate, Green, Oss
from .image import GenerateImage
require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "novelai"
plugin_keyword = "画个"
if hasattr(global_config, "environment") and global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword

data_base_col = {
    "token": "text",
    "last_time": "int",
}
novelai_db = Database()
if not novelai_db.init_table(table_name=plugin_name, table_key="id", table_key_type=int, table_col=data_base_col):
    raise Exception("init novelai_db table error")
global_core = GlobalCore()
green = Green(config.ali_access_id, config.ali_access_key, config.ali_region_sh)
translate = Translate(config.ali_access_id, config.ali_access_key, config.ali_region_hz)
oss = Oss(config.ali_access_id, config.ali_access_key, config.ali_region_sh, config.ali_oss_bucket_name,
          config.ali_oss_bucket_url)

bean_container = BeanContainer()
bean_container.register(novelai_db)
bean_container.register(config)
bean_container.register(translate)
bean_container.register(green)
bean_container.register(oss)

module_list = [
    GenerateImage(bean_container, plugin_keyword, "画个什么?\n"
                                                  "格式:画个+关键词+(换行)\n"
                                                  "(不要+关键词)+(换行)\n"
                                                  "(相似度0.3)+(图片),关键词用逗号分隔.\n"
                                                  "例如:\n"
                                                  "画个男孩,床上,玩游戏"
                                                  "不要女孩,桌子"
                                                  "相似度0.3[图片]"),
]


async def check_enable(event: GroupMessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

han = on_startswith(plugin_keyword, priority=1, rule=check_enable)


@han.handle()
async def handle(event: GroupMessageEvent):
    text = event.get_plaintext()
    if text == plugin_keyword:
        message = "指令格式：\n"
        for module in module_list:
            message += f"{module.get_keyword()}：{module.get_help()}\n"
        message = message.rstrip("\n")
        await han.finish(message)

    for module in module_list:
        if module.match_keyword(text):
            message = await module.handle_event(event)
            if message is not None:
                await han.finish(message)


