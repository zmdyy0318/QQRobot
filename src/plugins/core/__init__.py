import json
from nonebot import get_driver
from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent
from nonebot.log import logger
from .config import Config

from src.common_utils.database import Database

global_config = get_driver().config
config = Config.parse_obj(global_config)

data_base_col = {
    "enable": "int",
    "group_id_list": "text",
}

core_db = Database()
if not core_db.init_table(table_name="core", table_key="name", table_key_type=str, table_col=data_base_col):
    raise Exception("init core table error")
plugin_names = config.plugin_names
for plugin_name in plugin_names:
    success, exist = core_db.is_key_exist(plugin_name)
    if not success:
        raise Exception("init core key error")
    if not exist:
        core_db.insert_key(plugin_name)
        core_db.update_value(plugin_name, "enable", 1)
        core_db.update_value(plugin_name, "group_id_list", "[]")


core = on_startswith("设置")


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
    text = text.lstrip("设置").strip()
    if len(text) == 0:
        return
    fail_message = "设置失败,%s"
    for test_name in plugin_names:
        if text.find(test_name) == 0:
            text = text.lstrip(test_name).strip()
            if len(text) == 0:
                return
            if text.find("开启") == 0:
                ret = core_db.update_value(test_name, "enable", 1)
                if ret:
                    await core.finish(f"{test_name}已开启")
            elif text.find("关闭") == 0:
                ret = core_db.update_value(test_name, "enable", 0)
                if ret:
                    await core.finish(f"{test_name}已关闭")
            elif text.find("添加") == 0:
                text = text.lstrip("添加").strip()
                ret, group_id_list = core_db.get_value(test_name, "group_id_list")
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return

                try:
                    json_val: list = json.loads(group_id_list)
                except (Exception,) as e:
                    logger.error("{} handle error, e:{}", core, e)
                    await core.finish(fail_message % "json解析失败")
                    return
                if int(text) not in json_val:
                    json_val.append(int(text))
                ret = core_db.update_value(test_name, "group_id_list", json.dumps(json_val))
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return
                await core.finish(f"{test_name}已添加群{text}")
            elif text.find("删除") == 0:
                text = text.lstrip("删除").strip()
                ret, group_id_list = core_db.get_value(test_name, "group_id_list")
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return
                try:
                    json_val: list = json.loads(group_id_list)
                except (Exception,) as e:
                    logger.error("{} handle error, e:{}", core, e)
                    await core.finish(fail_message % "json解析失败")
                    return
                for group_id in json_val:
                    if str(group_id) == text:
                        json_val.remove(group_id)
                        break
                ret = core_db.update_value(test_name, "group_id_list", json.dumps(json_val))
                if ret is False:
                    await core.finish(fail_message % core_db.get_last_error_msg())
                    return
                await core.finish(f"{test_name}已删除群{text}")
            break
