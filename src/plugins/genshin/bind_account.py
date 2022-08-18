from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from src.common_utils.genshin_api import API
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent


class BindAccount(IPluginBase):
    __bind_tip = "PC打开https://bbs.mihoyo.com/ys/登陆后,右键检查,选择控制台,粘贴以下代码,在弹出的窗口点确认,然后粘贴发送,绑定完毕记得撤回：\n" \
                 "var cookie=document.cookie;" \
                 "var Str_Num=cookie.indexOf('_MHYUUID=');" \
                 "cookie='原神绑定'+cookie.substring(Str_Num);" \
                 "var ask=confirm('Cookie:'+cookie+'按确认,然后粘贴发送给机器人');" \
                 "if(ask==true){copy(cookie);msg=cookie}else{msg='Cancel'}"
    __bind_success = "绑定成功,请及时撤回绑定cookie\n%s"
    __bind_fail = "绑定失败,%s"

    def init_module(self):
        pass

    async def handle_event(self, event: GroupMessageEvent):
        from_id = int(event.get_user_id())
        plain_text = event.get_plaintext()
        plain_text = self.strip_keyword(plain_text)

        if len(plain_text) == 0:
            return self.__bind_tip

        gs = API()
        success, user_role = await gs.init_user_role(plain_text)
        if success is False:
            return self.__bind_fail % gs.get_last_error_msg()

        db: Database = self.bean_container.get_bean(Database)
        ret, exist = db.is_key_exist(from_id)
        if ret is False:
            return self.__bind_fail % db.get_last_error_msg()

        if exist is False:
            ret = db.insert_key(from_id)
            if ret is False:
                return self.__bind_fail % db.get_last_error_msg()

        ret = db.update_value(from_id, "cookie", plain_text)
        if ret is False:
            return self.__bind_fail % db.get_last_error_msg()

        message = f"uid:{user_role.game_uid}\n" \
                  f"昵称:{user_role.nickname}\n" \
                  f"等级:{user_role.level}"
        return self.__bind_success % message

    async def task(self, groups: list):
        pass
