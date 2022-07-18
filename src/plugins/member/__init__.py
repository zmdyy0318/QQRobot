import nonebot
from nonebot import require
from nonebot import get_driver
from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Event, GroupDecreaseNoticeEvent, GroupIncreaseNoticeEvent
from nonebot.log import logger
from .config import Config

from src.common_utils.database import Database
from src.common_utils.system import is_plugin_enable


require('core')

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "member"
core_db = Database()
if not core_db.connect_table("core"):
    raise Exception("connect core table error")


member = on_notice(priority=10)


@member.handle()
async def handle(event: Event):
    if not isinstance(event, GroupDecreaseNoticeEvent) and not isinstance(event, GroupIncreaseNoticeEvent):
        return

    enable = await is_plugin_enable(event, core_db, plugin_name)
    if enable is False:
        return

    bot = nonebot.get_bot()
    group_id = int(event.group_id)
    user_id = int(event.user_id)
    operator_id = int(event.operator_id)
    ret = await bot.get_stranger_info(user_id=user_id)
    user_name = ret["nickname"]
    if user_id == operator_id:
        operator_name = user_name
    else:
        ret = await bot.get_stranger_info(user_id=operator_id)
        operator_name = ret["nickname"]
    ret = await bot.get_group_info(group_id=group_id)
    group_name = ret["group_name"]

    for send_group_id in config.member_admin_groups:
        send_group_id = int(send_group_id)
        try:
            message = ""
            if isinstance(event, GroupDecreaseNoticeEvent):
                if event.sub_type == "kick":
                    message = f"成员变动:{user_id}({user_name})被{operator_id}({operator_name})踢出了{group_id}({group_name})"
                elif event.sub_type == "leave":
                    message = f"成员变动:{user_id}({user_name})离开了{group_id}({group_name})"
            elif isinstance(event, GroupIncreaseNoticeEvent):
                message = f"成员变动:{user_id}({user_name})加入了{group_id}({group_name})"
            if len(message) > 0:
                await bot.send_group_msg(group_id=send_group_id, message=message)
        except (Exception,) as e:
            logger.error(f"member::send error, e={e}, send_group_id={send_group_id}")

