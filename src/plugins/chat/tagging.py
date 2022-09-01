from src.common_utils.aliyun import NlpPos
from .attrs import STOP_WORDS, TAG_POS


class CustomLemmaTagger(object):

    def __init__(self, language=None):
        punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
        punctuation += r"""！“·”￥（），。、：；《》？【】…—「」 """
        self.punctuation_table = str.maketrans(dict.fromkeys(punctuation))
        self.stop_word = STOP_WORDS
        self.tag_pos = TAG_POS
        self.nlp: NlpPos = language
        self.language = "xx"

    def get_text_index_string(self, text: str):
        bigram_pairs = []

        if len(text) <= 2:
            text_without_punctuation = text.translate(self.punctuation_table)
            if len(text_without_punctuation) >= 1:
                text = text_without_punctuation

        ret, document = self.nlp.get_nlp_info_by_text(text)
        if ret is False:
            return text

        if len(text) <= 2:
            bigram_pairs = [
                token.word.lower() for token in document
            ]
        else:
            tokens = [
                token for token in document if token.word.isalpha() and token.word not in self.stop_word
            ]

            if len(tokens) < 2:
                tokens = [
                    token for token in document if token.word.isalpha()
                ]

            for index in range(1, len(tokens)):
                pos = tokens[index - 1].pos
                if pos in self.tag_pos:
                    pos_ = self.tag_pos[pos]
                else:
                    pos_ = "X"
                bigram_pairs.append('{}:{}'.format(
                    pos_,
                    tokens[index].word.lower()
                ))

        if not bigram_pairs:
            bigram_pairs = [
                token.word.lower() for token in document
            ]

        return ' '.join(bigram_pairs)
