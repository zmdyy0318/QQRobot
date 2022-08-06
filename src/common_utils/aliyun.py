import json
import uuid
import time
from abc import ABCMeta
from aliyunsdkcore import client
from aliyunsdkgreen.request.v20180509 import ImageSyncScanRequest
from aliyunsdkgreenextension.request.extension import HttpContentHelper
from aliyunsdkalinlp.request.v20200629 import GetPosChGeneralRequest
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr_api20210707.client import Client as OcrClient
from alibabacloud_ocr_api20210707 import models as OcrModels
from nonebot.log import logger


class ICore(metaclass=ABCMeta):
    __clt = None
    __config = None
    __region = None

    def __init__(self, key_id: str, key_secret: str, region: str):
        self.__clt = client.AcsClient(key_id, key_secret, region)
        self.__region = region
        self.__config = open_api_models.Config(
            access_key_id=key_id,
            access_key_secret=key_secret
        )

    def get_clt(self):
        return self.__clt

    def get_config(self):
        return self.__config

    def get_region(self):
        return self.__region


class Green(ICore):
    def get_image_score_by_url(self, urls: list) -> (bool, float):
        if len(urls) == 0:
            return True, 0.0
        return self.__do_request(urls)

    def __do_request(self, url: list) -> (bool, float):
        request = ImageSyncScanRequest.ImageSyncScanRequest()
        request.set_accept_format('JSON')
        task_list = []
        for u in url:
            task = {
                "dataId": str(uuid.uuid1()),
                "url": u
            }
            task_list.append(task)

        request.set_content(HttpContentHelper.toValue({"tasks": task_list, "scenes": ["porn"]}))
        return self.__do_action(request)

    def __do_action(self, request: ImageSyncScanRequest) -> (bool, float):
        score_sum = 0.0
        score_count = 0
        try:
            clt: client.AcsClient = self.get_clt()
            response = clt.do_action_with_exception(request)
            json_res = json.loads(response)
            if json_res["code"] != 200:
                logger.error(f"Green do_action_with_exception failed:{json_res['msg']}")
                return False, 0.0
            for data in json_res["data"]:
                if data["code"] != 200:
                    continue
                results = data["results"]
                if len(results) == 0:
                    continue
                score = float(results[0]["rate"])
                suggestion = results[0]["suggestion"]
                if suggestion == "pass":
                    score_sum += 0.0
                    score_count += 1
                elif suggestion == "review":
                    score_sum += (score / 2.0)
                    score_count += 1
                elif suggestion == "block":
                    score_sum += score
                    score_count += 1
                return True, score_sum / score_count
        except Exception as e:
            logger.error(f"Green do_action error, e:{e}")
            return False, 0.0


class NlpInfo:
    def __init__(self, pos: str, word: str):
        self.pos = pos
        self.word = word


class Nlp(ICore):
    def get_nlp_info_by_text(self, text: str) -> (bool, list):
        if len(text) == 0:
            return True, []
        # 防止频繁调用接口
        time.sleep(0.1)
        return self.__do_request(text)

    def __do_request(self, text: str) -> (bool, list):
        request = GetPosChGeneralRequest.GetPosChGeneralRequest()
        request.set_Text(text)
        request.set_OutType("1")
        request.set_ServiceCode("alinlp")
        request.set_TokenizerId("GENERAL_CHN")
        return self.__do_action(request)

    def __do_action(self, request: GetPosChGeneralRequest) -> (bool, list):
        try:
            clt: client.AcsClient = self.get_clt()
            response = clt.do_action_with_exception(request)
            json_res = json.loads(response)
            if not json_res:
                logger.error(f"Nlp do_action_with_exception failed")
                return False, []
            data = json_res["Data"]
            data_json = json.loads(data)
            result = data_json["result"]
            ret = []
            for item in result:
                ret.append(NlpInfo(item["pos"], item["word"]))
            return True, ret
        except Exception as e:
            logger.error(f"Nlp do_action error, e:{e}")
            return False, []


class OcrInfo:
    def __init__(self, text: str):
        self.text = text
        self.pos0 = [0, 0]
        self.pos1 = [0, 0]
        self.pos2 = [0, 0]
        self.pos3 = [0, 0]


class Ocr(ICore):
    def get_ocr_info_by_url(self, url: str) -> (bool, list):
        if len(url) == 0:
            return True, []
        return self.__do_request(url)

    def get_clt(self):
        config = self.get_config()
        config.endpoint = f"ocr-api.{self.get_region()}.aliyuncs.com"
        return OcrClient(config)

    def __do_request(self, url: str) -> (bool, list):
        request = OcrModels.RecognizeBasicRequest(
            url=url,
        )
        return self.__do_action(request)

    def __do_action(self, request) -> (bool, list):
        try:
            clt: OcrClient = self.get_clt()
            response = clt.recognize_basic(request)
            if response.status_code != 200:
                logger.error(f"Ocr __do_action recognize_basic failed, status_code:{response.status_code}")
                return False, []
            json_res = json.loads(response.body.data)
            if not json_res:
                logger.error(f"Ocr __do_action json.loads failed")
                return False, []
            num = json_res["prism_wnum"]
            if num == 0:
                return True, []
            words_list = json_res["prism_wordsInfo"]
            ret = []
            for word in words_list:
                info = OcrInfo(word["word"])
                info.pos0 = [word["pos"][0]["x"], word["pos"][0]["y"]]
                info.pos1 = [word["pos"][1]["x"], word["pos"][1]["y"]]
                info.pos2 = [word["pos"][2]["x"], word["pos"][2]["y"]]
                info.pos3 = [word["pos"][3]["x"], word["pos"][3]["y"]]
                ret.append(info)
            return True, ret
        except Exception as e:
            logger.error(f"Ocr do_action error, e:{e}")
            return False, []

