from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from src.common_utils.genshin_api import API
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent


class SignReward(IPluginBase):
    __sign_success = "签到成功,%s"
    __sign_fail = "签到失败,%s"

    def init_module(self):
        pass

    async def handle_event(self, event: GroupMessageEvent):
        from_id = int(event.get_user_id())
        plain_text = event.get_plaintext()
        plain_text = self.strip_keyword(plain_text)
        if len(plain_text) != 0:
            return None

        db: Database = self.bean_container.get_bean(Database)
        ret, cookie = db.get_value(from_id, "cookie")
        if ret is False:
            return self.__sign_fail % db.get_last_error_msg()
        if cookie is None or len(cookie) == 0:
            return self.__sign_fail % "未绑定cookie"

        gs = API()
        success, user_role = await gs.init_user_role(cookie)
        if success is False:
            return self.__sign_fail % gs.get_last_error_msg()
        success, sign_info = await gs.get_sign_info()
        if success is False:
            return self.__sign_fail % gs.get_last_error_msg()
        success, rewards_info = await gs.get_rewards_info()
        if success is False:
            return self.__sign_fail % gs.get_last_error_msg()

        total_sign_day = sign_info.total_sign_day
        sign_cnt_missed = sign_info.sign_cnt_missed
        is_sign = sign_info.is_sign
        if is_sign:
            today = total_sign_day - 1
        else:
            today = total_sign_day

        try:
            item_name = rewards_info.awards[today]["name"]
            item_count = rewards_info.awards[today]["cnt"]
        except (Exception,) as e:
            logger.error(f"SignReward rewards_info error, e:{e}, today:{today}")
            return self.__sign_fail % "参数错误"

        message_sign = f"今日物品{item_name}x{item_count}\n" \
                       f"本月已签{total_sign_day}天\n" \
                       f"本月漏签{sign_cnt_missed}天"

        if is_sign:
            message = "今天已经签到过了\n" + message_sign
            return self.__sign_fail % message

        success = await gs.act_sign()
        if success is False:
            return self.__sign_fail % gs.get_last_error_msg()

        message = message_sign
        return self.__sign_success % message

    async def task(self, groups: list):
        pass
