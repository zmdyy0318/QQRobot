import time
import json
import random
import hashlib
import string
import uuid
import httpx
from httpx import AsyncClient

from urllib.parse import urlencode

from nonebot.log import logger

'''
获取cookie
https://github.com/KimigaiiWuyi/GenshinUID/issues/255
'''


class API:

    __url_login_check_mobile_registered = "https://webapi.account.mihoyo.com/Api/is_mobile_registrable"

    __url_role_id = "https://api-takumi-record.mihoyo.com/game_record/app/card/wapi/getGameRecordCard"
    __url_role_index = "https://api-takumi.mihoyo.com/game_record/app/genshin/api/index"
    __url_role_characters = "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/character"
    __url_role_spiral_abyss = "https://api-takumi.mihoyo.com/game_record/app/genshin/api/spiralAbyss"
    __url_role_daily_note = "https://api-takumi.mihoyo.com/game_record/app/genshin/api/dailyNote"
    __url_role_journal_note = "https://hk4e-api.mihoyo.com/event/ys_ledger/monthInfo"

    __url_role_info = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie"
    __url_sign_info = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/info"
    __url_rewards_info = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/home"
    __url_sign = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/sign"

    __url_news = "https://bbs-api.mihoyo.com/post/api/getNewsList"

    # 请求头数据
    __headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.11.1",
        "Referer": "https://webstatic.mihoyo.com/",
        "x-rpc-app_version": "2.11.1",
        "x-rpc-client_type": "5",
        "DS": "",
        "Cookie": ""
    }

    __is_login = False
    __last_error_msg = ""
    __game_uid = ""
    __game_biz = ""
    __region = ""
    __nickname = ""
    __level = 0
    __cookie = ""

    class UserRole:
        def __init__(self, game_uid: str, game_biz: str, region: str, nickname: str, level: int):
            self.game_uid = game_uid
            self.game_biz = game_biz
            self.region = region
            self.nickname = nickname
            self.level = level

    async def init_user_role(self, cookie: str) -> (bool, UserRole):
        data_ret = await self.__get_role_info(cookie)
        if data_ret is None:
            return False, None
        if len(data_ret) == 0:
            logger.error("API::init_user_role error, no role")
            self.__last_error_msg = "没有找到角色,请检查米游社是否有原神数据"
            return False, None

        ret = data_ret[0]
        try:
            self.__game_uid = ret["game_uid"]
            self.__game_biz = ret["game_biz"]
            self.__region = ret["region"]
            self.__nickname = ret["nickname"]
            self.__level = ret["level"]
        except (Exception,) as e:
            logger.error(f"API::init_user_role dict error, e: {e}")
            self.__last_error_msg = "角色信息获取失败,请联系管理员"
            return False, None

        self.__cookie = cookie
        self.__is_login = True
        return True, self.UserRole(self.__game_uid, self.__game_biz, self.__region, self.__nickname, self.__level)

    class SignInfo:
        def __init__(self, is_sign: bool, sign_cnt_missed: int, today: str, total_sign_day: int):
            self.is_sign = is_sign
            self.sign_cnt_missed = sign_cnt_missed
            self.today = today
            self.total_sign_day = total_sign_day

    async def get_sign_info(self) -> (bool, SignInfo):
        data_ret = await self.__get_sign_info()
        if data_ret is None:
            return False, None
        try:
            is_sign: bool = data_ret["is_sign"]
            sign_cnt_missed: int = data_ret["sign_cnt_missed"]
            today: str = data_ret["today"]
            total_sign_day: int = data_ret["total_sign_day"]
        except (Exception,) as e:
            logger.error(f"API::init_user_role dict error, e: {e}")
            self.__last_error_msg = "签到信息获取失败,请联系管理员"
            return False, None
        return True, self.SignInfo(is_sign, sign_cnt_missed, today, total_sign_day)

    class RewardsInfo:
        def __init__(self, month: int, awards: list):
            self.month = month
            self.awards = awards

    async def get_rewards_info(self) -> (bool, SignInfo):
        data_ret = await self.__get_rewards_info()
        if data_ret is None:
            return False, None
        try:
            month: int = data_ret["month"]
            awards: list = data_ret["awards"]
            for award in awards:
                icon: str = award["icon"]
                name: str = award["name"]
                cnt: int = award["cnt"]

        except (Exception,) as e:
            logger.error(f"API::init_user_role dict error, e: {e}")
            self.__last_error_msg = "签到信息获取失败,请联系管理员"
            return False, None
        return True, self.RewardsInfo(month, awards)

    async def act_sign(self) -> bool:
        data_ret = await self.__act_sign()
        if data_ret is None:
            return False
        try:
            code: str = data_ret["code"]
        except (Exception,) as e:
            logger.error(f"API::init_user_role dict error, e: {e}")
            self.__last_error_msg = "签到失败,请联系管理员"
            return False
        if code != "ok":
            return False
        return True

    class NewsInfo:
        def __init__(self, news_list: list):
            self.news_list = news_list

    async def get_news(self, page_size: int, news_type: int) -> (bool, list):
        data_ret = await self.__get_news(page_size, news_type)
        if data_ret is None:
            return False, None
        try:
            news_list: list = data_ret["list"]
            for new in news_list:
                post_id: str = new["post"]["post_id"]
                subject: str = new["post"]["subject"]
                images: list = new["post"]["images"]
        except (Exception,) as e:
            logger.error(f"API::init_user_role dict error, e: {e}")
            self.__last_error_msg = "获取新闻失败,请联系管理员"
            return False, None
        return True, news_list

    def get_last_error_msg(self):
        error_msg = self.__last_error_msg
        self.__last_error_msg = ""
        return error_msg

    @staticmethod
    def __generate_230_headers(cookie: str, with_ds: bool = False):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) " \
             "AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.3.0"
        headers = {
            "User-Agent": ua,
            "Referer": "https://webstatic.mihoyo.com/",
            "Cookie": cookie
        }
        if with_ds:
            n = 'h8w582wxwgqvahcdkpvdhbh2w9casgfl'
            i = int(time.time())
            r = ''.join(random.sample(string.ascii_lowercase + string.digits, 6))
            d = "salt=%s&t=%d&r=%s" % (n, i, r)
            c = hashlib.md5(d.encode(encoding="UTF-8")).hexdigest()
            headers["DS"] = "%s,%s,%s" % (i, r, c)
            headers["x-rpc-app_version"] = "2.3.0"
            headers["x-rpc-client_type"] = "5"
            headers["x-rpc-device_id"] = str(uuid.uuid3(uuid.NAMESPACE_URL, ua)).replace('-', '').upper()
        return headers

    @staticmethod
    def __generate_211_headers(cookie: str, with_ds: bool = False, query: dict = {}, body: str = ""):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) " \
             "AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.11.1"
        headers = {
            "User-Agent": ua,
            "Referer": "https://webstatic.mihoyo.com/",
            "Cookie": cookie
        }
        if with_ds:
            n = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
            i = int(time.time())
            r = "".join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 6))
            q = urlencode(query)
            d = "salt=%s&t=%d&r=%s&b=%s&q=%s" % (n, i, r, body, q)
            c = hashlib.md5(d.encode(encoding="UTF-8")).hexdigest()
            headers["DS"] = "%s,%s,%s" % (i, r, c)
            headers["x-rpc-app_version"] = "2.3.0"
            headers["x-rpc-client_type"] = "5"
            headers["x-rpc-device_id"] = str(uuid.uuid3(uuid.NAMESPACE_URL, ua)).replace('-', '').upper()
        return headers

    @staticmethod
    def __calculate_ds(query: dict, body: str = ""):
        n = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
        i = int(time.time())
        r = "".join(random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 6))
        q = urlencode(query)
        d = "salt=%s&t=%d&r=%s&b=%s&q=%s" % (n, i, r, body, q)
        c = hashlib.md5(d.encode(encoding="UTF-8")).hexdigest()
        return "%s,%s,%s" % (i, r, c)

    async def __httpx_get_data(self, url: str, params: dict, headers: dict):
        try:
            async with AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.error(f"API::__httpx_get_data server error, code: {response.status_code}")
                    self.__last_error_msg = "服务器错误,请稍后再试"
                    return None
                json_ret = response.json()
                if json_ret["retcode"] != 0:
                    logger.error(f"API::__httpx_get_data ret code error, retcode:{json_ret['retcode']}, msg: {json_ret['message']}")
                    self.__last_error_msg = "返回错误,请检查cookie是否有效或重新绑定,错误内容: %s" % json_ret["message"]
                    return None
                ret = json_ret["data"]
                self.__last_error_msg = ""
                return ret
        except (Exception,) as e:
            logger.error(f"API::__httpx_get_data Exception error, e: {e}")
            self.__last_error_msg = "未知错误,请联系管理员"
            return None

    async def __httpx_post_data(self, url: str, params: dict, body: dict, headers: dict):
        headers["content-type"] = "application/json"
        try:
            async with AsyncClient() as client:
                response = await client.post(url, params=params, json=body, headers=headers)
                if response.status_code != 200:
                    logger.error(f"API::__httpx_post_data server error, code: {response.status_code}")
                    self.__last_error_msg = "服务器错误,请稍后再试"
                    return None
                json_ret = response.json()
                if json_ret["retcode"] != 0:
                    logger.error(f"API::__httpx_post_data ret code error, "
                                 f"retcode:{json_ret['code']}, msg: {json_ret['message']}")
                    self.__last_error_msg = "返回错误,请检查cookie是否有效,错误内容: %s" % json_ret["message"]
                    return None
                ret = json_ret["data"]
                self.__last_error_msg = ""
                return ret
        except (Exception,) as e:
            logger.error(f"API::__httpx_post_data Exception error, e: {e}")
            self.__last_error_msg = "未知错误,请联系管理员"
            return None

    # 获取角色信息
    async def __get_role_info(self, cookie: str):
        query = {
            "game_biz": "hk4e_cn"
        }
        headers = self.__generate_211_headers(cookie)
        data = await self.__httpx_get_data(self.__url_role_info, query, headers)
        if data is None:
            logger.error("API::__get_role_info error, data is None")
            return None
        if data["list"] is None:
            logger.error("API::__get_role_info error, list is None")
            self.__last_error_msg = "数据错误,请联系管理员"
            return None
        return data["list"]

    async def __get_sign_info(self):
        if self.__is_login is False:
            logger.error("API::__get_sign_info error, not login")
            self.__last_error_msg = "未登录,请绑定cookie"
            return None

        query = {
            "act_id": "e202009291139501",
            "uid": self.__game_uid,
            "region": self.__region
        }
        headers = self.__generate_211_headers(self.__cookie)
        data = await self.__httpx_get_data(self.__url_sign_info, query, headers)
        if data is None:
            logger.error("API::__get_sign_info error, data is None")
            return None
        return data

    async def __get_rewards_info(self):
        if self.__is_login is False:
            logger.error("API::__get_sign_info error, not login")
            self.__last_error_msg = "未登录,请绑定cookie"
            return None

        query = {
            "act_id": "e202009291139501"
        }
        headers = self.__generate_211_headers(self.__cookie)
        data = await self.__httpx_get_data(self.__url_rewards_info, query, headers)
        if data is None:
            logger.error("API::__get_sign_info error, data is None")
            return None
        return data

    async def __act_sign(self):
        if self.__is_login is False:
            logger.error("API::__act_sign error, not login")
            self.__last_error_msg = "未登录,请绑定cookie"
            return None
        query = {}
        body = {
            "act_id": "e202009291139501",
            "region": self.__region,
            "uid": self.__game_uid,
        }
        headers = self.__generate_230_headers(self.__cookie, with_ds=True)
        data = await self.__httpx_post_data(self.__url_sign, query, body, headers)
        if data is None:
            logger.error("API::__act_sign error, data is None")
            return None
        return data

    async def __get_news(self, page_size: int, news_type: int):
        query = {
            "gids": "2",
            "page_size":  page_size,
            "type": news_type
        }
        headers = self.__generate_211_headers("")
        data = await self.__httpx_get_data(self.__url_news, query, headers)
        if data is None:
            logger.error("API::__get_sign_info error, data is None")
            return None
        return data

    # 检查手机是否注册
    def login_check_mobile_registered(self, phoneNumber: str):
        query = {
            "mobile": phoneNumber,
            "t": time.time()
        }
        headers = self.__headers

        response = httpx.get(self.__url_login_check_mobile_registered, params=query, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            return None

    # 获取米游社账户下游戏列表
    def get_base_info(self, myid: str, cookie: str):
        query = {
            "uid": myid
        }
        headers = self.__headers
        headers["DS"] = self.__calculate_ds(query)
        headers["Cookie"] = cookie
        response = httpx.get(self.__url_role_id, params=query, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    # 获取账号具体信息
    def get_detail_info(self, uid: str, server: str, cookie: str):
        query = {
            "role_id": uid,
            "server": server
        }
        headers = self.__headers
        headers["DS"] = self.__calculate_ds(query)
        headers["Cookie"] = cookie

        response = httpx.get(self.__url_role_index, params=query, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    # 获取角色信息
    def get_characters_info(self, role_id: str, server: str, char_ids: list, cookie: str):
        body = {
            "character_ids": char_ids,
            "role_id": role_id,
            "server": server
        }
        headers = self.__headers
        headers["DS"] = self.__calculate_ds({}, json.dumps(body))
        headers["Cookie"] = cookie
        headers["content-type"] = "application/json"

        response = httpx.post(self.__url_role_characters, json=body, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    # 获深渊信息
    def get_spiral_abyss_info(self, role_id: str, server: str, period: str, cookie: str):
        query = {
            "role_id": role_id,
            "schedule_type": period,
            "server": server
        }
        headers = self.__headers
        headers["DS"] = self.__calculate_ds(query)
        headers["Cookie"] = cookie

        response = httpx.get(self.__url_role_spiral_abyss, params=query, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    # 获取每日相关信息
    def get_daily_note_info(self, uid: str, server: str, cookie: str):
        query = {
            "role_id": uid,
            "server": server
        }
        headers = self.__headers
        headers["DS"] = self.__calculate_ds(query)
        headers["Cookie"] = cookie

        response = httpx.get(self.__url_role_daily_note, params=query, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    # 获取每日相关信息
    def get_daily_journal_note(self, uid: str, bind_region: str, month: str, cookie: str):
        query = {
            "month": month,
            "bind_uid": uid,
            "bind_region": bind_region
        }
        headers = self.__headers
        headers["DS"] = self.__calculate_ds(query)
        headers["Cookie"] = cookie

        response = httpx.get(self.__url_role_journal_note, params=query, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

