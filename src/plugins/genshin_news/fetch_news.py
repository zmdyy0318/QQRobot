import nonebot
from src.common_utils.interface import IPluginBase
from src.common_utils.genshin_api import API
from src.common_utils.database import Database
from src.common_utils.system import JsonUtil
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment


class FetchNews(IPluginBase):
    __fetched_news = "获取新闻成功,%s"
    __fetch_fail = "获取新闻失败,%s"
    __bbs_url = "https://bbs.mihoyo.com/ys/article/"

    def init_module(self):
        pass

    async def handle_event(self, event: GroupMessageEvent):
        url_type = self.get_url_type()
        gs = API()
        success, news_list = await gs.get_news(3, url_type)
        if success is False:
            return self.__fetch_fail % gs.get_last_error_msg()

        if len(news_list) == 0:
            return self.__fetch_fail % "没有获取到新闻"

        message = Message([])
        for new in news_list:
            post = new["post"]
            post_id = post["post_id"]
            subject = post["subject"]
            images = post["images"]
            message += MessageSegment.text(f"{subject}\n")
            message += MessageSegment.text(f"{self.__bbs_url}{post_id}\n")
            if len(images) > 0:
                image_url = images[0]
                message += MessageSegment.image(image_url)
        return message

    async def task(self, groups: list):
        url_type = self.get_url_type()

        db: Database = self.bean_container.get_bean(Database)
        gs = API()

        success, news = await gs.get_news(15, url_type)
        if success is False:
            logger.error(f"FetchNews task get news error:{gs.get_last_error_msg()}")
            return

        for group in groups:
            group = int(group)
            ret, exist = db.is_key_exist(group)
            if ret is False:
                logger.error(f"FetchNews task is_key_exist failed:{db.get_last_error_msg()}")
                continue
            if exist is False:
                db.insert_key(group)
                db.update_value(group, "types", "[1, 3]")
                db.update_value(group, "post_ids", "[]")

            ret, db_types_str = db.get_value(group, "types")
            if ret is False:
                logger.error(f"FetchNews task get_value failed:{db.get_last_error_msg()}")
                continue
            ret, db_type_list = JsonUtil.json_str_to_list(db_types_str)
            if ret is False:
                logger.error(f"FetchNews task json_str_to_list failed:{db_types_str}")
                continue
            ret, db_post_ids_str = db.get_value(group, "post_ids")
            if ret is False:
                logger.error(f"FetchNews task get_value failed:{db.get_last_error_msg()}")
                continue
            ret, db_post_ids_list = JsonUtil.json_str_to_list(db_post_ids_str)
            if ret is False:
                logger.error(f"FetchNews task json_str_to_list failed:{db_post_ids_str}")
                continue

            if url_type not in db_type_list:
                continue

            message = Message([])
            send_count = 0
            for new in news:
                post = new["post"]
                post_id = int(post["post_id"])
                if post_id in db_post_ids_list:
                    continue
                subject = post["subject"]
                images = post["images"]
                db_post_ids_list.append(post_id)
                message += MessageSegment.text(f"{subject}\n")
                message += MessageSegment.text(f"{self.__bbs_url}{post_id}\n")
                if len(images) > 0:
                    image_url = post["images"][0]
                    message += MessageSegment.image(image_url)
                send_count += 1

            db_post_ids_list.sort()
            if len(db_post_ids_list) > 100:
                db_post_ids_list = db_post_ids_list[-100:]
            if send_count > 0:
                ret = db.update_value(group, "post_ids", JsonUtil.list_to_json_str(db_post_ids_list))
                if ret is False:
                    logger.error(f"FetchNews task update_value failed:{db.get_last_error_msg()}")
                    continue

            if 0 < send_count <= 12:
                bot = nonebot.get_bot()
                try:
                    await bot.send_group_msg(group_id=group, message=message)
                except Exception as e:
                    logger.error(f"FetchNews task send_group_msg error:{e}, group:{group}")
                    continue

    def get_url_type(self) -> int:
        key_word = self.get_keyword()
        if key_word.find("获取公告") >= 0:
            return 1
        elif key_word.find("获取活动") >= 0:
            return 2
        elif key_word.find("获取资讯") >= 0:
            return 3
        return 0
