from src.common_utils.aliyun import Green
from nonebot.log import logger
from httpx import AsyncClient
from src.common_utils.system import BeanContainer


class Image:
    __bean_container: BeanContainer

    def __init__(self, bean_container: BeanContainer):
        self.__bean_container = bean_container

    async def handle(self, urls: list) -> (bool, float):
        large_url_list = []
        for url in urls:
            if len(url) == 0:
                continue
            ret, image_size = await self.__get_url_content_size(url)
            if ret is False:
                continue
            # 50kb以下的图片不计算
            if image_size > 1024 * 50:
                large_url_list.append(url)

        green: Green = self.__bean_container.get_bean(Green)
        ret, score = green.get_image_score_by_url(large_url_list)
        logger.info(f"Image::get_image_score_by_url ret: {ret}, score: {score}")
        return ret, score

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
