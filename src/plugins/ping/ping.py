import httpx
import nonebot
from src.common_utils.interface import IPluginBase
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.log import logger
from .config import Config


class Ping(IPluginBase):
    __config: Config

    def init_module(self):
        self.__config = self.bean_container.get_bean(Config)

    async def handle_event(self, event: GroupMessageEvent):
        message = "ping"
        message += self.__ping_proxy()
        return message

    async def task(self, groups: list):
        message = "ping"
        message += self.__ping_proxy()
        bot = nonebot.get_bot()
        for group in groups:
            try:
                await bot.send_group_msg(group_id=group, message=message)
            except Exception as e:
                logger.error(f"send ping msg error, e:{e}")
                continue

    def __ping_proxy(self):
        proxy_url = f"http://{self.__config.proxy_host}:{self.__config.proxy_port}"
        ping_url = "http://www.google.com"
        ret_msg = "\nproxy "
        try:
            response = httpx.get(ping_url, proxies=proxy_url)
            elapsed_ms = response.elapsed.microseconds / 1000
            ret_msg += f"elapsed_ms: {elapsed_ms}"
        except (Exception,) as e:
            ret_msg += f"error: {e}"
        return ret_msg
