from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from src.common_utils.aliyun import NlpNer, NlpPos
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.log import logger


class What(IPluginBase):
    __db: Database
    __nlp_ner: NlpNer
    __nlp_pos: NlpPos

    def init_module(self):
        self.__db = self.bean_container.get_bean(Database)
        self.__nlp_ner = self.bean_container.get_bean(NlpNer)
        self.__nlp_pos = self.bean_container.get_bean(NlpPos)

    async def handle_event(self, event: GroupMessageEvent):
        text = event.get_plaintext()
        if len(text) == 0:
            return None

        if text.endswith(self.get_keyword()):
            ret, nlp_list = self.__nlp_pos.get_nlp_info_by_text(text)
            if ret is False:
                logger.error(f"What::handle_event get_nlp_info_by_text error, text: {text}")
                return None
            nlp_list.reverse()
            word_v = ""
            for nlp in nlp_list:
                if nlp.pos == "VV":
                    word_v = nlp.word
                    break
            if len(word_v) == 0:
                return None
            ret, ner_word = self.__get_ner_word()
            if ret is False or ner_word is None:
                return None
            return f"建议{word_v} {ner_word}"
        else:
            self.__insert_ner_word(text)

    async def task(self, groups: list):
        pass

    def __insert_ner_word(self, text) -> bool:
        ret, nlp_list = self.__nlp_ner.get_nlp_info_by_text(text)
        if ret is False:
            return False
        for nlp in nlp_list:
            if nlp.weight < 0.6:
                continue
            ret, exist = self.__db.is_values_exist({"tag": nlp.tag, "word": nlp.word})
            if ret is False:
                logger.error(f"What::__insert_ner_word is_values_exist error, text: {text}")
                continue
            if exist is True:
                continue
            ret = self.__db.insert_values({"tag": nlp.tag, "word": nlp.word})
            if ret is False:
                logger.error(f"What::__insert_ner_word insert_values error, text: {text}")

    def __get_ner_word(self) -> (bool, str):
        word = ""
        ret, val = self.__db.get_random_value("word", {"tag": "品牌"})
        if ret is True and val is not None:
            word += val
        ret, val = self.__db.get_random_value("word", {"tag": "修饰"})
        if ret is True and val is not None:
            word += val
        ret, val = self.__db.get_random_value("word", {"tag": "品类"})
        if ret is True and val is not None:
            word += val
        return True, word

