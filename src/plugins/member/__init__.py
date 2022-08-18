import nonebot
from nonebot import require
from nonebot import get_driver
from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Event, GroupDecreaseNoticeEvent, GroupIncreaseNoticeEvent
from nonebot.log import logger
from .config import Config

require('core')
from src.plugins.core.core import GlobalCore

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "member"
global_core = GlobalCore()


async def check_enable(event: Event) -> bool:
    if not isinstance(event, GroupDecreaseNoticeEvent) and not isinstance(event, GroupIncreaseNoticeEvent):
        return False
    return global_core.is_plugin_enable(plugin_name, event.group_id)

member = on_notice(priority=10, rule=check_enable)


@member.handle()
async def handle(event: Event):
    if not isinstance(event, GroupDecreaseNoticeEvent) and not isinstance(event, GroupIncreaseNoticeEvent):
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

