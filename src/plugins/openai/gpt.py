import time
import uuid
import json
import httpx
import re
import nonebot

from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from httpx import AsyncClient
from .config import Config


class GroupChatInfo:
    conversation_id: str
    parent_id: str

    def __init__(self, conversation_id, parent_id):
        self.conversation_id = conversation_id
        self.parent_id = parent_id


class ResponseInfo:
    context: str
    send_index: int

    def __init__(self):
        self.context = ""
        self.send_index = 0


class ChatGPT(IPluginBase):
    __conversation_id: str
    __parent_id: str
    __headers: dict
    __db: Database
    __config: Config
    __chat_fail = "我坏掉了,%s"
    __group_info_list: dict
    __response_info_list: dict

    __auth_authorization: str
    __auth_session_token: str

    def init_module(self):
        self.__headers = {
            "Accept": "application/json",
            "Authorization": "Bearer ",
            "Content-Type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        }
        self.__db = self.bean_container.get_bean(Database)
        self.__config = self.bean_container.get_bean(Config)
        self.__group_info_list = {}
        self.__response_info_list = {}

        self.__auth_authorization = ""
        self.__auth_session_token = ""

    async def handle_event(self, event: GroupMessageEvent):
        if not event.to_me:
            return
        if event.reply is not None:
            return
        plaintext = event.get_plaintext()
        if len(plaintext) <= 0:
            return

        ret = await self.__refresh_token()
        if ret is False:
            logger.error(f"__refresh_token failed")
            return self.__chat_fail % "刷新token失败"

        group_id = event.group_id
        if group_id not in self.__group_info_list:
            group_chat_info = GroupChatInfo(None, self.__generate_uuid())
            self.__group_info_list[group_id] = group_chat_info
        else:
            group_chat_info = self.__group_info_list[group_id]

        if plaintext == "重置":
            group_chat_info.conversation_id = None
            group_chat_info.parent_id = self.__generate_uuid()
            return "会话已重置"

        ret, conversation_id, parent_id, error = await self.__process_chat_response(event, plaintext, group_chat_info)
        if ret is False:
            return self.__chat_fail % "获取回复失败" + error

        group_chat_info.conversation_id = conversation_id
        group_chat_info.parent_id = parent_id
        return

    async def task(self, groups: list):
        await self.__refresh_token()

    async def __update_chat_message(self, event: GroupMessageEvent, message_id: str, text: str, is_end: bool):
        if message_id not in self.__response_info_list:
            self.__response_info_list[message_id] = ResponseInfo()
        response_info = self.__response_info_list[message_id]
        response_info.context = text
        new_text = text[response_info.send_index:]
        # 小于30个字符不处理
        if len(new_text) < 100 and is_end is False:
            return

        index_line = new_text.rfind("\n")
        # index_stop_cn = new_text.find("。")
        # index_stop_en = new_text.find(".")
        if index_line > 0:
            index = index_line
        # elif index_stop_cn > 0:
        #     index = index_stop_cn
        # elif index_stop_en > 0:
        #     index = index_stop_en
        elif is_end is True:
            index = len(new_text) - 1
        else:
            return

        send_text = new_text[:index + 1]
        response_info.send_index += len(send_text)

        message = Message([])
        message += MessageSegment.at(event.user_id)
        message += MessageSegment.text(send_text)
        if is_end:
            message += MessageSegment.text("[END]")
        else:
            message += MessageSegment.text("[WAITING]")
        try:
            bot = nonebot.get_bot()
            await bot.send_group_msg(group_id=event.group_id, message=message)
        except Exception as e:
            logger.error(f"__send_chat_message error:{e}")

    async def __process_chat_response(self, event: GroupMessageEvent,
                                      text: str, group_chat_info: GroupChatInfo) -> (bool, str, str, str):
        data = {
            "action": "next",
            "messages": [
                {
                    "id": str(self.__generate_uuid()),
                    "role": "user",
                    "content": {"content_type": "text", "parts": [text]}
                 }
            ],
            "conversation_id": group_chat_info.conversation_id,
            "parent_message_id": group_chat_info.parent_id,
            "model": "text-davinci-002-render"
        }
        url = "https://chat.openai.com/backend-api/conversation"
        try:
            conversation_id = ""
            parent_id = ""
            client = httpx.AsyncClient()
            async with client.stream("POST", url, headers=self.__headers, json=data, timeout=50) as response:
                if response.status_code != 200:
                    logger.error(f"__get_chat_response status_code failed, code:{response.status_code}")
                    return False, None, None, f"status_code:{response.status_code}"
                async for line in response.aiter_lines():
                    try:
                        if line == "" or line == "\n":
                            continue
                        data = line[6:]
                        if data == "[DONE]" or data == "[DONE]\n":
                            await self.__update_chat_message(event, parent_id, text, True)
                        else:
                            data_json = json.loads(data)
                            conversation_id = data_json["conversation_id"]
                            parent_id = data_json["message"]["id"]
                            parts = data_json["message"]["content"]["parts"]
                            if parts is None or len(parts) == 0:
                                continue
                            text = parts[0]
                            await self.__update_chat_message(event, parent_id, text, False)
                    except (Exception,) as e:
                        logger.warning(f"__get_chat_response aiter_lines failed, e:{e}, line:{line}")
                        continue

                return True, conversation_id, parent_id, None
        except (Exception,) as e:
            logger.error(f"__get_chat_response failed, e:{e}")
            return False, None, None, str(e)

    async def __refresh_token(self) -> bool:
        global_key = "global"
        ret, exist = self.__db.is_key_exist(global_key)
        if ret is False:
            logger.error(f"__refresh_token is_key_exist failed:{self.__db.get_last_error_msg()}")
            return False
        if exist is False:
            self.__db.insert_key(global_key)
            self.__db.update_value(global_key, "session_token", self.__config.openai_session_token)
            self.__db.update_value(global_key, "authorization", "")
            self.__db.update_value(global_key, "refresh_time", 0)

        ret, refresh_time = self.__db.get_value(global_key, "refresh_time")
        if ret is False:
            logger.error(f"__refresh_token get_value failed:{self.__db.get_last_error_msg()}")
            return False

        ret, session_token = self.__db.get_value(global_key, "session_token")
        if ret is False:
            logger.error(f"__refresh_token get_value failed:{self.__db.get_last_error_msg()}")
            return False

        ret, authorization = self.__db.get_value(global_key, "authorization")
        if ret is False:
            logger.error(f"__refresh_token get_value failed:{self.__db.get_last_error_msg()}")
            return False

        current_time = int(time.time())
        if current_time - refresh_time < 60 * 30 \
                and len(session_token) > 0 \
                and len(authorization) > 0:
            self.__auth_session_token = session_token
            self.__auth_authorization = authorization
            self.__headers["Authorization"] = f"Bearer {authorization}"
            return True

        ret, session_token, authorization = await self.__update_token(session_token)
        if ret is False:
            logger.error(f"__update_token failed")
            return False

        self.__auth_session_token = session_token
        self.__auth_authorization = authorization
        self.__headers["Authorization"] = f"Bearer {authorization}"
        self.__db.update_value(global_key, "refresh_time", current_time)
        self.__db.update_value(global_key, "session_token", session_token)
        self.__db.update_value(global_key, "authorization", authorization)
        return True

    @staticmethod
    async def __update_token(session_token: str) -> (bool, str, str):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
        }
        cookies = {
            "__Secure-next-auth.session-token": session_token
        }
        url = "https://chat.openai.com/api/auth/session"
        try:
            async with httpx.AsyncClient(headers=headers, cookies=cookies) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.error(f"__update_token get failed:{response.status_code}")
                    return False, "", ""
                json_res = json.loads(response.text)
                if not json_res:
                    logger.error(f"__update_token get failed, json_res is None")
                    return False, "", ""
                return True, response.cookies["__Secure-next-auth.session-token"], json_res["accessToken"]
        except Exception as e:
            logger.error(f"__update_token failed:{e}")
            return False, "", ""

    @staticmethod
    def __generate_uuid():
        return str(uuid.uuid4())
