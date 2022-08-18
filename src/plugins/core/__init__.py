import json
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent
from nonebot.log import logger
from .config import Config
from .core import GlobalCore

from src.common_utils.system import JsonUtil

global_config = get_driver().config
config = Config.parse_obj(global_config)
plugin_name = "core"
plugin_keyword = "设置"
if global_config.environment == "dev":
    plugin_keyword = "/" + plugin_keyword


plugin_names = config.plugin_names
global_core = GlobalCore()
global_core.init_core_db(config.plugin_names)
core_db = global_core.get_core_db()


core = on_startswith(plugin_keyword, priority=1)


@core.handle()
async def handle(event: Event):
    is_normal_user = True
    if isinstance(event, GroupMessageEvent):
        is_normal_user = event.sender.role == "member"
    for super_user in global_config.superusers:
        if int(event.get_user_id()) == int(super_user):
            is_normal_user = False
            break

    if is_normal_user:
        return

    text = event.get_plaintext()
    text = text.lstrip(plugin_keyword).strip()
    if len(text) == 0:
        return
    fail_message = "设置失败,%s"
    for test_name in plugin_names:
        if text.find(test_name) == 0:
            text_cmd = text.lstrip(test_name).strip()
            if len(text_cmd) == 0:
                return
            if text_cmd.find("开启") == 0:
                ret = core_db.update_value(test_name, "enable", 1)
                if ret:
                    await core.finish(f"{test_name}已开启")
            elif text_cmd.find("关闭") == 0:
                ret = core_db.update_value(test_name, "enable", 0)
                if ret:
                    await core.finish(f"{test_name}已关闭")
            elif text_cmd.find("添加") == 0:
                text_cmd = text_cmd.lstrip("添加").strip()
                ret, group_id_list = core_db.get_value(test_name, "group_id_list")
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return

                ret, json_val = JsonUtil.json_str_to_list(group_id_list)
                if ret is False:
                    await core.finish(fail_message % "json解析失败")
                    return

                if int(text_cmd) not in json_val:
                    json_val.append(int(text_cmd))
                ret = core_db.update_value(test_name, "group_id_list", JsonUtil.list_to_json_str(json_val))
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return
                await core.finish(f"{test_name}已添加群{text_cmd}")
            elif text_cmd.find("删除") == 0:
                text_cmd = text_cmd.lstrip("删除").strip()
                ret, group_id_list = core_db.get_value(test_name, "group_id_list")
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return
                try:
                    json_val: list = json.loads(group_id_list)
                except (Exception,) as e:
                    logger.error(f"{core} handle error, e:{e}")
                    await core.finish(fail_message % "json解析失败")
                    return
                for group_id in json_val:
                    if str(group_id) == text_cmd:
                        json_val.remove(group_id)
                        break
                ret = core_db.update_value(test_name, "group_id_list", json.dumps(json_val))
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return
                await core.finish(f"{test_name}已删除群{text_cmd}")

