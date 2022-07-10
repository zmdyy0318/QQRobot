import json
import uuid
from aliyunsdkcore import client
from aliyunsdkgreen.request.v20180509 import ImageSyncScanRequest
from aliyunsdkgreenextension.request.extension import HttpContentHelper
from nonebot.log import logger


class Green:
    __access_key_id: str
    __access_key_secret: str
    __region: str
    __clt = None

    def init_access_key(self, key_id: str, key_secret: str, region: str) -> bool:
        self.__clt = client.AcsClient(key_id, key_secret, region)
        return True

    async def get_image_score_by_url(self, urls: list) -> (bool, float):
        if len(urls) == 0:
            return False, 0.0
        return await self.__do_request(urls)

    async def __do_request(self, url: list) -> (bool, float):
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
        return await self.__do_action(request)

    async def __do_action(self, request: ImageSyncScanRequest) -> (bool, float):
        score_sum = 0.0
        score_count = 0
        try:
            response = self.__clt.do_action_with_exception(request)
            json_res = json.loads(response)
            if json_res["code"] != 200:
                logger.error("Green get_image_score_by_url failed:%s" % json_res["msg"])
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
            logger.error("Green do_action error, e:{}", e)
            return False, 0.0

