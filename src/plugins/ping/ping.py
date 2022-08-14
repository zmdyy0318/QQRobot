import httpx
from src.common_utils.system import BeanContainer
from .config import Config


class Ping:
    __bean_container: BeanContainer
    __config: Config

    def __init__(self, bean_container: BeanContainer):
        self.__bean_container = bean_container
        self.__config = bean_container.get_bean(Config)

    async def ping_proxy(self):
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
