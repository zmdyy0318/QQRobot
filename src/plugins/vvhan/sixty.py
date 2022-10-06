import json
import nonebot
import httpx
import io
from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment


class Sixty(IPluginBase):
    __fetched_news = "获取新闻成功,%s"
    __fetch_fail = "获取新闻失败,%s"
    __url = "https://api.vvhan.com/api/60s"
    __db: Database

    def init_module(self):
        self.__db = self.bean_container.get_bean(Database)

    async def handle_event(self, event: GroupMessageEvent):
        ret, buffer = self.__get_image()
        if ret is False:
            return self.__fetch_fail % "获取图片失败"
        return Message(MessageSegment.image(buffer))

    async def task(self, groups: list):
        ret, time_flag = self.__get_time_flag()
        if ret is False or len(time_flag) == 0:
            logger.error(f"Sixty::task __get_time_flag failed")
            return

        for group in groups:
            group = int(group)
            ret, exist = self.__db.is_key_exist(group)
            if ret is False:
                logger.error(f"Sixty::task is_key_exist failed:{self.__db.get_last_error_msg()}")
                continue
            if exist is False:
                self.__db.insert_key(group)

            ret, db_last_flag_str = self.__db.get_value(group, "last_60s_flag")
            if ret is False:
                logger.error(f"Sixty::task get_value failed:{self.__db.get_last_error_msg()}")
                continue

            if db_last_flag_str == time_flag or db_last_flag_str == "0":
                continue
            elif db_last_flag_str is None:
                self.__db.update_value(group, "last_60s_flag", time_flag)
                continue
            else:
                self.__db.update_value(group, "last_60s_flag", time_flag)
                ret, buffer = self.__get_image()
                if ret is False:
                    logger.error(f"Sixty::task __get_image failed")
                    continue
                message = Message(MessageSegment.image(buffer))
                try:
                    await nonebot.get_bot().send_group_msg(group_id=group, message=message)
                except Exception as e:
                    logger.error(f"Sixty::task send_group_msg failed:{e}")
                    continue

    def __get_time_flag(self) -> (bool, str):
        try:
            response = httpx.get(self.__url + "?type=json")
            if response.status_code != 200:
                logger.error(f"Sixty::__get_time_flag failed, status_code:{response.status_code}")
                return False, None
            json_res = json.loads(response.text)
            if not json_res:
                logger.error(f"Sixty::__get_time_flag failed, json_res is None")
                return False, None
            if json_res["success"] is not True:
                logger.error(f"Sixty::__get_time_flag failed, success is False")
                return False, None
            flag = json_res["time"][0]
            return True, flag
        except (Exception,) as e:
            logger.error(f"Sixty::__get_time_flag failed, e:{e}")
            return False, None

    def __get_image(self) -> (bool, io.BytesIO):
        try:
            response = httpx.get(self.__url, follow_redirects=True)
            if response.status_code != 200:
                logger.error(f"Sixty::__get_image failed, status_code:{response.status_code}")
                return False, None
            return True, io.BytesIO(response.content)
        except (Exception,) as e:
            logger.error(f"Sixty::__get_image failed, e:{e}")
            return False, None

