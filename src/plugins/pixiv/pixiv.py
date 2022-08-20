import io
import time
import httpx
import random
import nonebot
import xml.etree.ElementTree as ET
from urllib import parse
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

        if item is None:
            return "没有找到涩图,稍后再试试"

        url_list = []
        try:
            html = BeautifulSoup(item.description, "html.parser")
            images = html.find_all("img")
            for image in images:
                url_list.append(image["src"])
            if is_r18:
                r18_msg = "涩涩"
            else:
                r18_msg = "图片"
            info = f'{item.title}\n' \
                   f'{html.find("p").text}\n' \
                   f'pixiv id:{item.link.split("/")[-1]}\n' \
                   f'正在获取{len(images)}张{r18_msg}...'
            await bot.send_group_msg(group_id=group_id, message=info)
        except Exception as e:
            logger.error(f"Pixiv handle_event parse html failed:{e}")
            return self.__fail_message

        db.update_value(group_id, "last_time", int(time.time()))

        ret, buffer = self.__image_to_gif(url_list)
        if ret is True and buffer is not None:
            return Message(MessageSegment.image(buffer))

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
        keyword_url = parse.quote(keyword)
        urls = [
            f"https://rsshub.app/pixiv/search/{keyword_url}/normal/{mode}",
            f"https://rsshub.app/pixiv/search/{keyword_url}/popular/{mode}",
        ]
        try:
            items = []
            for url in urls:
                response = httpx.get(url, proxies=self.__proxy_url)
                if response.status_code != 200:
                    continue
                root = ET.fromstring(response.text)
                items.extend(root.findall("./channel/item"))

            if len(items) == 0:
                return True, None
            index = random.randint(0, len(items) - 1)
            item = PixivItem()
            item.title = items[index].find("title").text
            item.link = items[index].find("link").text
            item.description = items[index].find("description").text
            return True, item
        except (Exception,) as e:
            logger.error(f"__get_search_item failed, e:{e}")
            return False, None

    def __image_to_gif(self, urls: list) -> (bool, io.BytesIO):
        try:
            images = []
            for url in urls:
                response = httpx.get(url, proxies=self.__proxy_url)
                if response.status_code != 200:
                    logger.error(f"Repeat __image_to_gif get_image failed:{url} {response.status_code}")
                    continue
                image = Image.open(io.BytesIO(response.content))
                if image is None:
                    logger.error(f"Repeat __image_to_gif open image failed:{url}")
                    continue
                image.thumbnail((1024, 768), Image.ANTIALIAS)
                images.append(image)
            if len(images) == 0:
                return True, None
            image_cover = images[0].convert("1")
            buffer = io.BytesIO()
            image_cover.save(buffer, format="GIF", save_all=True, append_images=images,
                             duration=1000, loop=0)
            return True, buffer
        except Exception as e:
            logger.error(f"Repeat __image_to_gif failed:{e}")
            return False, None
