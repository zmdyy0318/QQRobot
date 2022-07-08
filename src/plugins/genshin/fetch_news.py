from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from .api import API
from nonebot.log import logger


class FetchNews(IPluginBase):
    __fetched_news = "获取新闻成功,%s"
    __fetch_fail = "获取新闻失败,%s"

    async def handle(self, from_id: int, plain_text: str):
        logger.info("FetchNews handle from_id:%d plain_text:%s" % (from_id, plain_text))
        db: Database = self.bean_container.get_bean(Database)

        gs = API()
        for i in range(0, 3):
            success, news_list = await gs.get_news(10, 1)
            if success is False:
                return self.__fetch_fail % gs.get_last_error_msg()

