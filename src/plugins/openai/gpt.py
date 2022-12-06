import time
import uuid
import json
import httpx
import re

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


class ChatGPT(IPluginBase):
    __conversation_id: str
    __parent_id: str
    __headers: dict
    __db: Database
    __config: Config
    __chat_fail = "我坏掉了,%s"
    __group_info_list: dict

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

        ret, response_text, con_id = await self.__get_chat_response(plaintext, group_chat_info)
        if ret is False:
            return self.__chat_fail % "获取回复失败" + response_text

        group_chat_info.conversation_id = con_id
        message = Message([])
        message += MessageSegment.at(event.user_id)
        message += MessageSegment.text(response_text)
        return message

    async def task(self, groups: list):
        await self.__refresh_token()

    async def __get_chat_response(self, text: str, group_chat_info: GroupChatInfo) -> (bool, str, str):
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
            async with AsyncClient() as client:
                response = await client.post(url, headers=self.__headers, json=data, timeout=20)
                if response.status_code != 200:
                    logger.error(f"__get_chat_response failed, code:{response.status_code}")
                    return False, str(response.status_code), ""
                response_text = response.text.replace("data: [DONE]", "")
                data = re.findall(r'data: (.*)', response_text)[-1]
                json_ret = json.loads(data)
                return True, json_ret["message"]["content"]["parts"][0], json_ret["conversation_id"]
        except Exception as e:
            logger.error(f"__get_chat_response failed, e:{e}")
            return False, str(e), ""

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
