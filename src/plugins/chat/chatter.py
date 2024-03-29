from src.common_utils.system import BeanContainer
from src.common_utils.aliyun import NlpPos
from src.common_utils.database import Database
from src.common_utils.interface import IPluginBase
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from .config import Config
from .tagging import CustomLemmaTagger
from .attrs import STOP_WORDS
import time


class MessageCache:
    message: list
    last_cache_time: int
    last_send_time: int
    next_interval: int


class Chatter(IPluginBase):
    __config: Config
    __message_cache: dict
    __default_interval: int
    __nlp = None
    __chatbot = None
    __stop_words = STOP_WORDS
    __statement_db: Database()

    def init_module(self):
        self.__config = self.bean_container.get_bean(Config)
        self.__nlp: NlpPos = self.bean_container.get_bean(NlpPos)
        self.__message_cache = {}
        self.__default_interval = 60 * 10
        success, bot = self.__create_bot(0)
        if success is False:
            raise Exception("create bot error")
        self.__chatbot = bot

        self.__statement_db = Database()
        if not self.__statement_db.connect_table("statement", self.__config.maria_chat_database):
            raise Exception("connect statement table error")

    async def handle_event(self, event: GroupMessageEvent):
        plain_text = event.get_plaintext()
        if len(plain_text) == 0 or plain_text.strip() == "":
            return
        if event.reply is not None \
                and event.reply.sender.user_id == event.self_id \
                and plain_text == "不可以":
            search_text = event.reply.message.extract_plain_text()
            db_ret, exist = self.__statement_db.is_value_exist("text", search_text)
            if db_ret is False:
                return "下次还敢"
            if exist is False:
                return "不是我说的"
            remove_ret = self.__statement_db.delete_value("text", search_text)
            if remove_ret is False:
                return "下次还敢"
            else:
                return "我错了"
        elif event.to_me:
            # @事件由其他插件处理
            return
        else:
            handle_ret, reply_text = self.__process_chat(event.group_id, plain_text)
            if handle_ret is False or len(reply_text) == 0:
                return None
            return reply_text

    async def task(self, groups: list):
        pass

    def __process_chat(self, group_id: int, plain_text: str) -> (bool, str):
        if len(plain_text) == 0:
            return False, ""

        response = None
        if len(plain_text) > 2:
            ret, document = self.__nlp.get_nlp_info_by_text(plain_text)
            if ret is True:
                tokens = [
                    token for token in document if token.word.isalpha() and token.word not in self.__stop_words
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

        if response is not None and 0.7 < response.confidence < 1 \
                and int(time.time()) - message_cache.last_send_time > 60:
            message_cache.last_send_time = int(time.time())
            # 删除回复后学习队列仍然存在
            # message_cache.message.append(response.text)
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

