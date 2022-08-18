import nonebot
import time
import random
import io
import httpx
from nonebot.log import logger
from src.common_utils.system import BeanContainer
from src.common_utils.database import Database
from src.common_utils.aliyun import Ocr
from src.common_utils.interface import IPluginBase
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from PIL import Image, ImageOps


class GroupInfo:
    last_message = None
    count = 0

    def __init__(self, last_message, count):
        self.last_message = last_message
        self.count = count


class Repeat(IPluginBase):
    __group_map = {}

    def init_module(self):
        pass

    async def handle_event(self, event: GroupMessageEvent):
        ret = self.__handle_image(event)
        if ret is not None:
            return ret
        ret = self.__handle_message(event)
        if ret is not None:
            return ret

        return None

    async def task(self, groups: list):
        pass

    def __handle_message(self, event: GroupMessageEvent):
        group_id = int(event.group_id)

        if group_id not in self.__group_map:
            self.__group_map[group_id] = GroupInfo(event.message, 1)
            return None

        if self.__group_map[group_id].last_message != event.message:
            self.__group_map[group_id].count = 1
            self.__group_map[group_id].last_message = event.message
            return None
        self.__group_map[group_id].count += 1

        if self.__group_map[group_id].count == 3:
            return event.message

    def __handle_image(self, event: GroupMessageEvent):
        ret_message = None
        data_list = []
        for seg in event.get_message():
            if seg.type == "image":
                file = seg.data["file"]
                if file is None or len(file) == 0:
                    continue
                data_list.append(seg.data)

        if len(data_list) == 0:
            return

        group_id = int(event.group_id)
        db: Database = self.bean_container.get_bean(Database)
        for data in data_list:
            file = data["file"]
            url = data["url"]
            ret, exist = db.is_key_exist(file)
            if ret is False:
                logger.error(f"Repeat __handle_image is_key_exist failed:{file} {db.get_last_error_msg()}")
                continue
            if exist is False:
                db.insert_key(file)
                db.update_value(file, "cur_num", 1)
                next_num = random.randint(3, 10)
                db.update_value(file, "next_num", next_num)
                db.update_value(file, "last_time", int(time.time()))
            else:
                ret, cur_num = db.get_value(file, "cur_num")
                if ret is False:
                    logger.error(f"Repeat __handle_image cur_num get_value failed:{file} {db.get_last_error_msg()}")
                    continue
                ret, next_num = db.get_value(file, "next_num")
                if ret is False:
                    logger.error(f"Repeat __handle_image next_num get_value failed:{file} {db.get_last_error_msg()}")
                    continue
                cur_num += 1
                if cur_num >= next_num:
                    db.update_value(file, "cur_num", 0)
                    next_num = random.randint(3, 10)
                    db.update_value(file, "next_num", next_num)
                    ret, buffer = self.__flip_image(url)
                    if ret is True and buffer is not None:
                        message = Message(MessageSegment.image(buffer))
                        ret_message = message
                else:
                    db.update_value(file, "cur_num", cur_num)
                db.update_value(file, "last_time", int(time.time()))
        return ret_message

    def __flip_image(self, url: str) -> (bool, io.BytesIO):
        ocr: Ocr = self.bean_container.get_bean(Ocr)
        try:
            response = httpx.get(url)
            if response.status_code != 200:
                logger.error(f"Repeat __flip_image get_image failed:{url} {response.status_code}")
                return False, None
            image = Image.open(io.BytesIO(response.content))
            if image is None:
                logger.error(f"Repeat __flip_image open image failed:{url}")
                return False, None
            if image.format == "GIF":
                return False, None
            ret, ocr_list = ocr.get_ocr_info_by_url(url)
            if ret is False:
                logger.error(f"Repeat __flip_image get_ocr_info_by_url failed:{url} {ocr.get_last_error_msg()}")
                return False, None
            mirror_image = ImageOps.mirror(image)
            for ocr_info in ocr_list:
                left = min(ocr_info.pos0[0], ocr_info.pos1[0],
                           ocr_info.pos2[0], ocr_info.pos3[0])
                top = min(ocr_info.pos0[1], ocr_info.pos1[1],
                          ocr_info.pos2[1], ocr_info.pos3[1])
                right = max(ocr_info.pos0[0], ocr_info.pos1[0],
                            ocr_info.pos2[0], ocr_info.pos3[0])
                bottom = max(ocr_info.pos0[1], ocr_info.pos1[1],
                             ocr_info.pos2[1], ocr_info.pos3[1])
                center = [int(image.width / 2), int(image.height / 2)]
                crop_image = image.crop((left, top, right, bottom))
                left = center[0] + (center[0] - left)
                right = center[0] + (center[0] - right)
                left, right = right, left
                mirror_image.paste(crop_image, (left, top, right, bottom))
            buffer = io.BytesIO()
            mirror_image.save(buffer, format=image.format)
            return True, buffer
        except Exception as e:
            logger.error(f"Repeat __flip_image failed:{url} {e}")
            return False, None
