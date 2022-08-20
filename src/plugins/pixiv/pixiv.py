import io
import time
import httpx
import random
import nonebot
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from src.common_utils.system import Database
from src.common_utils.interface import IPluginBase
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
from nonebot.log import logger
from PIL import Image
from .config import Config


class PixivItem:
    title: str
    link: str
    description: str


class Pixiv(IPluginBase):
    __fail_message = "涩涩失败,稍后再涩涩"
    __db: Database
    __config: Config
    __proxy_url: str

    def init_module(self):
        self.__db = self.bean_container.get_bean(Database)
        self.__config = self.bean_container.get_bean(Config)
        self.__proxy_url = f"http://{self.__config.proxy_host}:{self.__config.proxy_port}"

    async def handle_event(self, event: GroupMessageEvent):
        group_id = int(event.group_id)
        self_id = int(event.self_id)
        plain_text = event.get_plaintext()
        plain_text = self.strip_keyword(plain_text)

        if len(plain_text) == 0:
            return self.get_help()

        is_r18 = False
        if plain_text.endswith("涩图"):
            is_r18 = True
            plain_text = plain_text[:-2]

        if len(plain_text) > 20:
            return "短一点,短一点"

        db: Database = self.bean_container.get_bean(Database)
        ret, exist = db.is_key_exist(group_id)
        if ret is False:
            logger.error(f"Pixiv handle_event is_key_exist failed:{db.get_last_error_msg()}")
            return self.__fail_message
        if exist is False:
            db.insert_key(group_id)
            db.update_value(group_id, "mode", "day_female_r18")
            db.update_value(group_id, "last_time", 0)

        # 冷却时间
        ret, last_time = db.get_value(group_id, "last_time")
        if ret is False:
            logger.error(f"Pixiv handle_event get_value failed:{db.get_last_error_msg()}")
        cur_time = int(time.time())
        if cur_time - last_time < 60:
            return f"休息,休息{60 - (cur_time - last_time)}秒"

        bot = nonebot.get_bot()
        try:
            if is_r18:
                message = "涩涩..."
            else:
                message = "图片..."
            if len(plain_text) == 0:
                message += "随机"
            else:
                message += plain_text
            await bot.send_group_msg(group_id=group_id, message=message)
        except Exception as e:
            logger.error(f"Pixiv handle_event send_group_msg failed:{e}")
            return self.__fail_message

        if len(plain_text) == 0:
            ret, mode = db.get_value(group_id, "mode")
            if ret is False:
                logger.error(f"Pixiv handle_event get_value failed:{db.get_last_error_msg()}")
                return self.__fail_message
            ret, item = self.__get_ranking_item(mode)
            if ret is False:
                return self.__fail_message
        else:
            ret, item = self.__get_search_item(plain_text, is_r18)
            if ret is False:
                return self.__fail_message

        message = self.__pixiv_item_to_message(item, self_id)
        if message is None:
            return self.__fail_message

        try:
            await bot.send_group_forward_msg(group_id=group_id, messages=message)
            db.update_value(group_id, "last_time", int(time.time()))
        except Exception as e:
            logger.error(f"Pixiv handle_event send_group_forward_msg failed:{e}")
            return self.__fail_message

    async def task(self, groups: list):
        pass

    def __get_ranking_item(self, mode: str) -> (bool, PixivItem):
        url = f"https://rsshub.app/pixiv/ranking/{mode}"
        try:
            response = httpx.get(url, proxies=self.__proxy_url)
            if response.status_code != 200:
                logger.error(f"__get_ranking_item failed, status_code:{response.status_code}")
                return False, None
            root = ET.fromstring(response.text)
            items = root.findall("./channel/item")
            if len(items) == 0:
                return False, None
            index = random.randint(0, len(items) - 1)
            item = PixivItem()
            item.title = items[index].find("title").text
            item.link = items[index].find("link").text
            item.description = items[index].find("description").text
            return True, item
        except (Exception,) as e:
            logger.error(f"__get_ranking_item failed, e:{e}")
            return False, None

    def __get_search_item(self, keyword: str, is_r18: bool):
        mode = 1
        if is_r18:
            mode = 2
        url = f"https://rsshub.app/pixiv/search/{keyword}/popular/{mode}"
        try:
            response = httpx.get(url, proxies=self.__proxy_url)
            if response.status_code != 200:
                logger.error(f"__get_search_item failed, status_code:{response.status_code}")
                return False, None
            root = ET.fromstring(response.text)
            items = root.findall("./channel/item")
            if len(items) == 0:
                return False, None
            index = random.randint(0, len(items) - 1)
            item = PixivItem()
            item.title = items[index].find("title").text
            item.link = items[index].find("link").text
            item.description = items[index].find("description").text
            return True, item
        except (Exception,) as e:
            logger.error(f"__get_search_item failed, e:{e}")
            return False, None

    def __pixiv_item_to_message(self, item: PixivItem, send_id: int):
        try:
            message_list = []
            html = BeautifulSoup(item.description, "html.parser")
            images = html.find_all("img")
            info = f'{item.title}\n' \
                   f'{html.find("p").text}\n' \
                   f'pixiv id:{item.link.split("/")[-1]}\n' \
                   f'image count:{len(images)}'
            message_list.append(MessageSegment.node_custom(send_id, "114514", info))
            for image in images:
                ret, buffer = self.__random_image(image["src"])
                if ret is False or buffer is None:
                    continue
                msg_image = MessageSegment.image(buffer)
                message_list.append(MessageSegment.node_custom(send_id, "114514", Message(msg_image)))
            message = Message(message_list)
            return message
        except Exception as e:
            logger.error(f"__pixiv_item_to_message failed, e:{e}")
            return None

    def __random_image(self, url: str) -> (bool, io.BytesIO):
        try:
            response = httpx.get(url, proxies=self.__proxy_url)
            if response.status_code != 200:
                logger.error(f"Repeat __random_image get_image failed:{url} {response.status_code}")
                return False, None
            image = Image.open(io.BytesIO(response.content))
            if image is None:
                logger.error(f"Repeat __random_image open image failed:{url}")
                return False, None
            width = image.width
            height = image.height
            image.putpixel((width - 1, height - 1), image.getpixel((0, 0)))
            buffer = io.BytesIO()
            image.save(buffer, format=image.format)
            return True, buffer
        except Exception as e:
            logger.error(f"Repeat __random_image failed:{url} {e}")
            return False, None
