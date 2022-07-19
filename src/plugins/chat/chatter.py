from src.common_utils.system import BeanContainer
from nonebot.log import logger
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from .config import Config
import time
import spacy


class Language:
    ISO_639_1 = 'zh_core_web_md'


class MessageCache:
    message: list
    last_time: int
    next_interval: int


class Chatter:
    __bean_container: BeanContainer
    __chatbot_list: dict
    __config: Config
    __message_cache: dict
    __default_interval: int
    __nlp = None

    def __init__(self, bean_container: BeanContainer):
        self.__bean_container = bean_container
        self.__config = bean_container.get_bean(Config)
        self.__chatbot_list = {}
        self.__message_cache = {}
        self.__default_interval = 60 * 10
        self.__nlp = spacy.load(Language.ISO_639_1.lower())

    async def handle(self, group_id: int, plain_text: str) -> (bool, str):
        if len(plain_text) == 0:
            return False, ""

        if group_id not in self.__chatbot_list:
            success, bot = self.__create_bot(group_id)
            if success is False:
                return False, ""
            self.__chatbot_list[group_id] = bot

        bot: ChatBot = self.__chatbot_list[group_id]
        if len(plain_text) <= 2:
            response = None
        else:
            document = self.__nlp(plain_text)
            count = 0
            for token in document:
                if token.is_alpha and not token.is_stop:
                    count += 1
            if count <= 2:
                response = None
            else:
                response = bot.get_response(plain_text)

        self.__train_bot(bot, group_id)

        if group_id not in self.__message_cache:
            message_cache = MessageCache()
            message_cache.message = [plain_text]
            message_cache.last_time = int(time.time())
            message_cache.next_interval = self.__default_interval
            self.__message_cache[group_id] = message_cache
        else:
            message_cache = self.__message_cache[group_id]
            if len(message_cache.message) == 0 or message_cache.message[-1] != plain_text:
                message_cache.message.append(plain_text)
            message_cache.last_time = int(time.time())
            if message_cache.next_interval > 10:
                message_cache.next_interval = message_cache.next_interval - 10

        if response is not None and 0.5 <= response.confidence < 1:
            return True, response.text
        return False, ""

    def __create_bot(self, group_id: int) -> (bool, ChatBot):
        try:
            url = f"mysql+pymysql://{self.__config.maria_user}:" \
                  f"{self.__config.maria_password}@" \
                  f"{self.__config.maria_host}:" \
                  f"{self.__config.maria_port}/" \
                  f"{self.__config.maria_chat_database}"
            chatbot = ChatBot(
                str(group_id),
                storage_adapter="chatterbot.storage.SQLStorageAdapter",
                database_uri=url,
                tagger_language=Language,
                default_response=["None"],
                read_only=True
            )
            return True, chatbot
        except Exception as e:
            logger.error(f"Chatter::__create_bot error, e:{e}, group_id:{group_id}")
            return False, None

    def __train_bot(self, bot: ChatBot, group_id: int):
        if group_id not in self.__message_cache:
            return
        message_cache = self.__message_cache[group_id]
        try:
            if len(message_cache.message) == 0:
                return
            current_time = int(time.time())
            if current_time - message_cache.last_time < message_cache.next_interval:
                return
            if len(message_cache.message) == 1:
                message_cache.message.clear()
                message_cache.next_interval = self.__default_interval
                return
            trainer = ListTrainer(bot, show_training_progress=False)
            trainer.train(message_cache.message)
            message_cache.message.clear()
            message_cache.next_interval = self.__default_interval
            return
        except Exception as e:
            logger.error(f"Chatter::__train_bot error, e:{e}, group_id:{group_id}")
            message_cache.message.clear()
            message_cache.next_interval = self.__default_interval
            return
