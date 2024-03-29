import json
import nonebot
import httpx
import io
import re
import time
from base64 import b64decode, b64encode
from novelai_api import NovelAI_API, NovelAIError
from src.common_utils.interface import IPluginBase
from src.common_utils.database import Database
from src.common_utils.aliyun import Translate, Green, Oss
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from PIL import Image
from .config import Config


class GenerateImage(IPluginBase):
    __success_message = "操作成功,%s"
    __fail_message = "操作失败,%s"
    __url = "https://api.novelai.net"
    __db: Database
    __translate: Translate
    __config: Config
    __green: Green
    __oss: Oss
    __proxy_url: str

    def init_module(self):
        self.__db = self.bean_container.get_bean(Database)
        self.__config = self.bean_container.get_bean(Config)
        self.__translate = self.bean_container.get_bean(Translate)
        self.__green = self.bean_container.get_bean(Green)
        self.__oss = self.bean_container.get_bean(Oss)
        self.__proxy_url = f"http://{self.__config.proxy_host}:{self.__config.proxy_port}"

    async def handle_event(self, event: GroupMessageEvent):
        group_id = int(event.group_id)
        plain_text = event.get_plaintext()
        plain_text = self.strip_keyword(plain_text)

        if len(plain_text) == 0:
            return self.get_help()

        model_name = "nai-diffusion"
        model_name_cn = "普通"
        if plain_text.find("福瑞") == 0:
            plain_text = plain_text[2:]
            model_name = "nai-diffusion-furry"
            model_name_cn = "福瑞"

        if len(plain_text) > 10000:
            return "短一点,短一点"

        # 初始化
        ret, exist = self.__db.is_key_exist(group_id)
        if ret is False:
            logger.error(f"Image::handle_event is_key_exist failed:{self.__db.get_last_error_msg()}")
            return self.__fail_message % "数据库错误"
        if exist is False:
            self.__db.insert_key(group_id)
            self.__db.update_value(group_id, "last_time", 0)

        # 冷却时间
        ret, last_time = self.__db.get_value(group_id, "last_time")
        if ret is False:
            logger.error(f"Image::handle_event get_value failed:{self.__db.get_last_error_msg()}")
            return self.__fail_message % "数据库错误"
        cur_time = int(time.time())
        if cur_time - last_time < 10:
            return f"休息,休息{10 - (cur_time - last_time)}秒"

        # 翻译
        keyword = plain_text.replace("，", ",").replace("\n", " ").replace("\r", " ").replace("\t", " ")
        explict_keyword = ""

        similar = 0.3
        similar_match = re.search(r"相似度(\d.\d*)", keyword)
        if similar_match is not None:
            similar = float(similar_match.group(1))
            keyword = keyword.replace(f"相似度{similar}", "")
            if similar < 0:
                similar = 0
            elif similar >= 1:
                similar = 0.99

        explict_pos = keyword.find("不要")
        if explict_pos != -1:
            explict_keyword = keyword[explict_pos + 2:]
            keyword = keyword[:explict_pos]

        ret, keyword_en = self.__translate.translate(keyword, "zh", "en")
        if ret is False:
            return self.__fail_message % "翻译失败"

        ret, explict_keyword_en = self.__translate.translate(explict_keyword, "zh", "en")
        if ret is False:
            return self.__fail_message % "翻译失败"

        self.__db.update_value(group_id, "last_time", int(time.time()))
        ret, token = self.__db.get_value(group_id, "token")
        if ret is False:
            logger.error(f"Image::handle_event get_value failed:{self.__db.get_last_error_msg()}")
            return self.__fail_message % "数据库错误"

        image = None
        for seg in event.get_message():
            if seg.type == "image":
                ret, image = await self.__get_image(seg.data["url"])
                if ret is False:
                    return self.__fail_message % "下载图片失败"

        bot = nonebot.get_bot()
        try:
            info = f'正在画画......\n' \
                   f'包含{keyword_en}'
            if len(explict_keyword_en) > 0:
                info += f'\n排除{explict_keyword_en}'
            if image is not None:
                info += f'\n使用图片{image.width}x{image.height}'
                info += f'\n相似度{similar}'
            if keyword_en.find(",") <= 0 and keyword.find(" ") >= 0:
                info += f'\n关键词之间记得用逗号分开哦'
            await bot.send_group_msg(group_id=group_id, message=info)
        except Exception as e:
            logger.error(f"Image::handle_event send info failed:{e}")
            return self.__fail_message % "发送信息失败"

        # 验证token
        point = 0
        need_login = False
        if token is not None:
            ret, message, point = await self.__get_point(token)
            if ret is False:
                need_login = True
        else:
            need_login = True

        if need_login:
            ret, message, token = await self.__login(self.__config.nai_username, self.__config.nai_password)
            if ret is False:
                return self.__fail_message % f"登录失败:{message}"
            self.__db.update_value(group_id, "token", token)

            ret, message, point = await self.__get_point(token)
            if ret is False:
                return self.__fail_message % f"获取积分失败:{message}"

        ret, message, buffer = await self.__generate_image(token, model_name, keyword_en, explict_keyword_en, similar,
                                                           True, image)
        if ret is False or len(buffer) == 0:
            try:
                await bot.send_group_msg(group_id=group_id, message=f"生成图片失败:{message}, 正在重试......")
            except Exception as e:
                logger.error(f"Image::handle_event send info failed:{e}")
                return self.__fail_message % "发送信息失败"
            ret, message, buffer = await self.__generate_image(token, model_name, keyword_en, explict_keyword_en, similar,
                                                               False, image)
            if ret is False or len(buffer) == 0:
                return self.__fail_message % f"生成图片失败:{message}, 请稍后再试"

        buffer_bytes = b64decode(buffer)
        ret, score = self.__green.get_image_score_by_bytes(io.BytesIO(buffer_bytes))
        if ret is False:
            return self.__fail_message % "图片检查失败"

        if score > 0.5:
            save_path = f"novelai/{group_id}/{int(time.time())}.png"
            ret = self.__oss.upload_file(save_path, buffer_bytes)
            sign_url = ""
            if ret is True:
                ret, sign_url = self.__oss.get_sign_url(save_path, 10 * 60)
            if len(sign_url) == 0:
                ret_msg = "画好了,太涩了,没处理好"
            else:
                ret_msg = f"画好了,太涩了,在这里:\n" \
                          f"{sign_url}\n" \
                          f"10分钟过期"
        else:
            ret_msg = MessageSegment.image(f"base64://{buffer}")

        try:
            await bot.send_group_msg(group_id=group_id, message=ret_msg)
        except Exception as e:
            logger.error(f"Image::handle_event send image failed:{e}")
            return self.__fail_message % "发送图片失败"

        return None

    async def task(self, groups: list):
        pass

    @staticmethod
    async def __login(username, password) -> (bool, str, str):
        try:
            api = NovelAI_API()
            token = await api.high_level.login(username, password)
            return True, None, token
        except (Exception,) as e:
            logger.error(f"Image::__login failed, e:{e}")
            return False, str(e), None

    @staticmethod
    async def __get_point(token) -> (bool, str, int):
        try:
            api = NovelAI_API()
            api.headers["Authorization"] = f"Bearer {token}"
            data = await api.low_level.get_data()
            steps_left = data["subscription"]["trainingStepsLeft"]
            point = steps_left["fixedTrainingStepsLeft"] + steps_left["purchasedTrainingSteps"]
            return True, None, point
        except (Exception,) as e:
            logger.error(f"Image::__get_point failed, e:{e}")
            return False, str(e), None

    @staticmethod
    async def __get_image(url: str) -> (bool, Image):
        try:
            response = httpx.get(url)
            if response.status_code != 200:
                logger.error(f"Repeat __flip_image get_image get failed:{url} {response.status_code}")
                return False, None
            buffer = io.BytesIO(response.content)
            image = Image.open(buffer)
            if image is None:
                logger.error(f"Repeat __flip_image get_image open failed:{url} image is None")
                return False, None
            return True, image
        except Exception as e:
            logger.error(f"Image::__get_image failed:{url} {e}")
            return False, None

    async def __generate_image(self, token: str, model: str,
                               keyword_en: str, explict_keyword_en: str, similar: float,
                               use_proxy: bool = False,
                               image: Image = None) -> (bool, str, str):
        try:
            keyword_en = keyword_en + "masterpiece, best quality, "
            low_quality = 'nsfw, lowres, text, cropped, worst quality, low quality, normal quality, ' \
                          'jpeg artifacts, signature, watermark, username, blurry'
            bad_anatomy = 'bad anatomy, bad hands, error, missing fingers, extra digit, fewer digits'
            if len(explict_keyword_en) > 0:
                uc = explict_keyword_en
            else:
                uc = low_quality + ", " + bad_anatomy
            header = {
                "Authorization": f"Bearer {token}",
                "Authority": "api.novelai.net",
                "Content-Type": "application/json",
                "Referer": "https://novelai.net/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            if image is None:
                body = {
                    "input": keyword_en,
                    "model": model,
                    "parameters": {
                        "height": 512,
                        "width": 512,
                        "n_samples": 1,
                        "sampler": "k_euler_ancestral",
                        "scale": 11,
                        "steps": 28,
                        "uc": uc,
                        "ucPreset": 0,
                        "seed": int(time.time()),
                    }
                }
            else:
                image_width = image.width
                image_height = image.height
                if image_width > image_height:
                    if image_height / image_width > 0.95:
                        image_width = 512
                        image_height = 512
                    elif image_height / image_width > 0.85:
                        image_width = 576
                        image_height = 512
                    elif image_height / image_width > 0.75:
                        image_width = 640
                        image_height = 512
                    elif image_height / image_width > 0.65:
                        image_width = 704
                        image_height = 512
                    elif image_height / image_width > 0.55:
                        image_width = 832
                        image_height = 512
                    elif image_height / image_width > 0.45:
                        image_width = 1024
                        image_height = 512
                    elif image_height / image_width > 0.35:
                        image_width = 1280
                        image_height = 512
                    elif image_height / image_width > 0.25:
                        image_width = 1728
                        image_height = 512
                    else:
                        image_width = 512
                        image_height = 512
                elif image_width < image_height:
                    if image_width / image_height > 0.95:
                        image_width = 512
                        image_height = 512
                    elif image_width / image_height > 0.85:
                        image_width = 512
                        image_height = 576
                    elif image_width / image_height > 0.75:
                        image_width = 512
                        image_height = 640
                    elif image_width / image_height > 0.65:
                        image_width = 512
                        image_height = 704
                    elif image_width / image_height > 0.55:
                        image_width = 512
                        image_height = 832
                    elif image_width / image_height > 0.45:
                        image_width = 512
                        image_height = 1024
                    elif image_width / image_height > 0.35:
                        image_width = 512
                        image_height = 1280
                    elif image_width / image_height > 0.25:
                        image_width = 512
                        image_height = 1728
                    else:
                        image_width = 512
                        image_height = 512
                else:
                    image_width = 512
                    image_height = 512
                # if image_width > image_height:
                #     image_height = int(image_height * 512 / image_width)
                #     image_width = 512
                # else:
                #     image_width = int(image_width * 512 / image_height)
                #     image_height = 512
                # image = image.resize((image_width, image_height))
                buffer = io.BytesIO()
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.save(buffer, format="JPEG")
                img_str = b64encode(buffer.getvalue()).decode("utf-8")
                body = {
                    "input": keyword_en,
                    "model": model,
                    "parameters": {
                        "height": image_height,
                        "width": image_width,
                        "n_samples": 1,
                        "noise": (1.0 - similar) / 3.5,
                        "sampler": "k_euler_ancestral",
                        "scale": 11,
                        "steps": 50,
                        "strength": 1.0 - similar,
                        "uc": uc,
                        "ucPreset": 0,
                        "image": img_str,
                        "seed": int(time.time()),
                    }
                }
            proxy_url = None
            if use_proxy:
                proxy_url = self.__proxy_url
            async with httpx.AsyncClient(headers=header, timeout=40, proxies=proxy_url) as client:
                response = await client.post(self.__url + "/ai/generate-image", json=body)
                if response.status_code != 201:
                    logger.error(f"Image::__generate_image failed, status_code:{response.status_code}")
                    return False, str(response.status_code), None
                base64_str = response.text[27:]
                return True, str(response.status_code), base64_str
        except (Exception,) as e:
            logger.error(f"Image::__generate_image failed, e:{e}")
            return False, str(e), None

