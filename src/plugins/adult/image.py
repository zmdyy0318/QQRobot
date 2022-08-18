from src.common_utils.aliyun import Green
from src.common_utils.interface import IPluginBase
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from httpx import AsyncClient


class Image(IPluginBase):
    def init_module(self):
        pass

    async def handle_event(self, event: GroupMessageEvent):
        url_list = []
        for seg in event.get_message():
            if seg.type == "image":
                url = seg.data["url"]
                if len(url) != 0:
                    url_list.append(seg.data["url"])

        large_url_list = []
        for url in url_list:
            ret, image_size = await self.__get_url_content_size(url)
            if ret is False:
                continue
            # 10kb以下的图片不计算
            if image_size > 1024 * 10:
                large_url_list.append(url)

        if len(large_url_list) == 0:
            return None

        green: Green = self.bean_container.get_bean(Green)
        ret, score = green.get_image_score_by_url(large_url_list)
        if ret is False or score < 0.5:
            return None

        count = round(score / 20.0) + 1
        return "💦" * count

    async def task(self, groups: list):
        pass

    @staticmethod
    async def __get_url_content_size(url: str) -> (bool, int):
        try:
            async with AsyncClient() as client:
                response = await client.head(url)
                if response.status_code != 200:
                    logger.error(f"Image::__get_url_content_size error, code:{response.status_code}, url:{url}")
                    return False, 0
                return True, int(response.headers["Content-Length"])
        except Exception as e:
            logger.error(f"Image::__get_url_content_size error, e:{e}, url:{url}")
            return False, 0
