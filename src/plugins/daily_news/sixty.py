import nonebot
import httpx
import pathlib
import io
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from src.common_utils.interface import IPluginBase
from src.common_utils.genshin_api import API
from src.common_utils.database import Database
from src.common_utils.system import JsonUtil
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from PIL import Image, ImageDraw, ImageFont
from .config import Config


class RssItem:
    title: str
    link: str
    description: str


class Sixty(IPluginBase):
    __fetched_news = "获取新闻成功,%s"
    __fetch_fail = "获取新闻失败,%s"
    __url = "https://rsshub.app/liulinblog/kuaixun"
    __db: Database
    __config: Config
    __proxy_url: str

    def init_module(self):
        self.__db = self.bean_container.get_bean(Database)
        self.__config = self.bean_container.get_bean(Config)
        self.__proxy_url = f"http://{self.__config.proxy_host}:{self.__config.proxy_port}"

    async def handle_event(self, event: GroupMessageEvent):
        ret, rss_list = self.__get_item()
        if ret is False:
            return self.__fetch_fail % "网络错误"
        if len(rss_list) == 0:
            return self.__fetch_fail % "没有获取到新闻"

        rss_item = rss_list[0]
        ret, buffer = self.__item_to_image(rss_item)
        if ret is False or buffer is None:
            return self.__fetch_fail % "生成图片失败"

        return Message(MessageSegment.image(buffer))

    async def task(self, groups: list):
        ret, rss_list = self.__get_item()
        if ret is False or len(rss_list) == 0:
            logger.error(f"Sixty::task __get_item failed")
            return

        for group in groups:
            group = int(group)
            ret, exist = self.__db.is_key_exist(group)
            if ret is False:
                logger.error(f"Sixty::task is_key_exist failed:{self.__db.get_last_error_msg()}")
                continue
            if exist is False:
                self.__db.insert_key(group)
                self.__db.update_value(group, "post_ids", "[]")

            ret, db_post_ids_str = self.__db.get_value(group, "post_ids")
            if ret is False:
                logger.error(f"Sixty::task get_value failed:{self.__db.get_last_error_msg()}")
                continue
            ret, db_post_ids_list = JsonUtil.json_str_to_list(db_post_ids_str)
            if ret is False:
                logger.error(f"Sixty::task json_str_to_list failed:{db_post_ids_str}")
                continue

            message = Message([])
            send_items = []
            for rss_item in rss_list:
                post_id = int(rss_item.link.split("/")[-1].replace(".html", ""))
                if post_id in db_post_ids_list:
                    continue
                db_post_ids_list.append(post_id)
                send_items.append(rss_item)

            db_post_ids_list.sort()
            if len(db_post_ids_list) > 100:
                db_post_ids_list = db_post_ids_list[-100:]
            if len(send_items) > 0:
                ret = self.__db.update_value(group, "post_ids", JsonUtil.list_to_json_str(db_post_ids_list))
                if ret is False:
                    logger.error(f"Sixty::task update_value failed:{self.__db.get_last_error_msg()}")
                    continue

            if len(send_items) == 1:
                for rss_item in send_items:
                    ret, buffer = self.__item_to_image(rss_item)
                    if ret is False or buffer is None:
                        logger.error(f"Sixty::task __item_to_image failed")
                        continue
                    message += MessageSegment.image(buffer)
                    try:
                        await nonebot.get_bot().send_group_msg(group_id=group, message=message)
                    except Exception as e:
                        logger.error(f"Sixty::task send_group_msg failed:{e}")
                        continue

    def __get_item(self) -> (bool, list):
        ret = []
        try:
            response = httpx.get(self.__url, proxies=self.__proxy_url)
            if response.status_code != 200:
                logger.error(f"Sixty::__get_item failed, status_code:{response.status_code}")
                return False, None
            root = ET.fromstring(response.text)
            items = root.findall("./channel/item")
            if len(items) == 0:
                return False, ret
            for item in items:
                rss_item = RssItem()
                rss_item.title = item.find("title").text
                rss_item.link = item.find("link").text
                rss_item.description = item.find("description").text
                ret.append(rss_item)
            return True, ret
        except (Exception,) as e:
            logger.error(f"Sixty::__get_ranking_item failed, e:{e}")
            return False, ret

    def __get_image_by_url(self, url) -> (bool, io.BytesIO):
        try:
            response = httpx.get(url, proxies=self.__proxy_url)
            if response.status_code != 200:
                logger.error(f"Sixty::__get_image_by_url failed, status_code:{response.status_code}")
                return False, None
            return True, io.BytesIO(response.content)
        except (Exception,) as e:
            logger.error(f"Sixty::__get_image_by_url failed, e:{e}")
            return False, None

    def __item_to_image(self, item: RssItem) -> (bool, io.BytesIO):
        try:
            font_path = pathlib.Path(__file__).parent / "simhei.ttf"
            font = ImageFont.truetype(str(font_path), 25)

            html = BeautifulSoup(item.description, "html.parser")
            node_ps = html.find_all("p")

            full_width = 600
            image_out = Image.new("RGB", (full_width, 12000), (255, 255, 255))
            draw = ImageDraw.Draw(image_out)

            current_height = 0
            for node_p in node_ps:
                node_imgs = node_p.find_all("img")
                for node_img in node_imgs:
                    url = node_img.attrs["src"]
                    ret, byte = self.__get_image_by_url(url)
                    if ret is False:
                        continue
                    image = Image.open(byte)
                    image.thumbnail((full_width - 10, 600))
                    image = image.convert("RGB")
                    image_out.paste(image, (5, current_height, full_width - 5, current_height + image.height))
                    current_height += image.height + 10
                text = node_p.text.strip()
                if len(text) == 0:
                    continue
                for line in self.__wrap_text(text, font, full_width - 20):
                    draw.text((10, current_height), line, font=font, fill=(0, 0, 0))
                    current_height += font.getsize(line)[1] + 10
                current_height += + 20
            buffer = io.BytesIO()
            image_out = image_out.crop((0, 0, full_width, current_height))
            image_out.save(buffer, format="JPEG")
            return True, buffer
        except (Exception,) as e:
            logger.error(f"Sixty::__item_to_image failed, e:{e}")
            return False, None

    @staticmethod
    def __wrap_text(text: str, font: ImageFont, width: int) -> list:
        text_lines = []
        text_line = ""
        for word in text:
            text_line += word
            w, h = font.getsize(text_line)
            if w > width:
                text_line = text_line[:-1]
                text_lines.append(text_line)
                text_line = word

        if len(text_line) > 0:
            text_lines.append(text_line)

        return text_lines
