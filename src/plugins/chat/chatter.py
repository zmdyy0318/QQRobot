from src.common_utils.system import BeanContainer
from nonebot.log import logger
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from .config import Config
from .tagging import CustomLemmaTagger
from .attrs import STOP_WORDS
from src.common_utils.aliyun import Nlp
from src.common_utils.database import Database
import time


class MessageCache:
    message: list
    last_cache_time: int
    last_send_time: int
    next_interval: int


class Chatter:
    __bean_container: BeanContainer
    __config: Config
    __message_cache: dict
    __default_interval: int
    __nlp = None
    __chatbot = None

    def __init__(self, bean_container: BeanContainer):
        self.__bean_container = bean_container
        self.__config = bean_container.get_bean(Config)
        self.__nlp: Nlp = bean_container.get_bean(Nlp)
        self.stop_word = STOP_WORDS
        self.__message_cache = {}
        self.__default_interval = 60 * 10
        success, bot = self.__create_bot(0)
        if success is False:
            raise Exception("create bot error")
        self.__chatbot = bot

        self.__statement_db = Database()
        if not self.__statement_db.connect_table("statement", self.__config.maria_chat_database):
            raise Exception("connect statement table error")

    async def delete_reply(self, plain_text: str) -> bool:
        return self.__statement_db.delete_value("text", plain_text)

    async def handle(self, group_id: int, plain_text: str) -> (bool, str):
        if len(plain_text) == 0:
            return False, ""

        response = None
        if len(plain_text) > 2:
            ret, document = self.__nlp.get_nlp_info_by_text(plain_text)
            if ret is True:
                tokens = [
                    token for token in document if token.word.isalpha() and token.word not in self.stop_word
                ]
                if len(tokens) >= 2:
                    response = self.__chatbot.get_response(plain_text)

        self.__train_bot(self.__chatbot, group_id)

        if group_id not in self.__message_cache:
            message_cache = MessageCache()
            message_cache.message = [plain_text]
            message_cache.last_cache_time = int(time.time())
            message_cache.next_interval = self.__default_interval
            message_cache.last_send_time = 0
            self.__message_cache[group_id] = message_cache
        else:
            message_cache = self.__message_cache[group_id]
            if len(message_cache.message) == 0 or message_cache.message[-1] != plain_text:
                message_cache.message.append(plain_text)
            message_cache.last_cache_time = int(time.time())
            if message_cache.next_interval > 10:
                message_cache.next_interval = message_cache.next_interval - 10

        if response is not None and 0.5 < response.confidence < 1 \
                and int(time.time()) - message_cache.last_send_time > 60:
            message_cache.last_send_time = int(time.time())
            message_cache.message.append(response.text)
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
                default_response=["None"],
                tagger=CustomLemmaTagger,
                tagger_language=self.__nlp,
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
            if current_time - message_cache.last_cache_time < message_cache.next_interval:
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
