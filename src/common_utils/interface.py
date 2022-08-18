from abc import ABCMeta, abstractmethod
from .system import BeanContainer
from nonebot.adapters.onebot.v11 import Event


class IPluginBase(metaclass=ABCMeta):
    __keyword: str
    __help_text: str
    bean_container: BeanContainer

    def __init__(self, bean_container: BeanContainer, keyword: str = "", help_text: str = ""):
        self.__keyword = keyword
        self.__help_text = help_text
        self.bean_container = bean_container
        self.init_module()

    def match_keyword(self, plain_text: str) -> bool:
        if plain_text.find(self.__keyword) == 0:
            return True
        else:
            return False

    def strip_keyword(self, plain_text: str) -> str:
        return plain_text.lstrip(self.__keyword)

    def get_keyword(self) -> str:
        return self.__keyword

    def get_help(self) -> str:
        return self.__help_text

    @abstractmethod
    def init_module(self):
        pass

    @abstractmethod
    async def handle_event(self, event: Event):
        pass

    @abstractmethod
    async def task(self, groups: list):
        pass
