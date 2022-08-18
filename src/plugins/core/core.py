from src.common_utils.system import Singleton, JsonUtil
from src.common_utils.database import Database


class GlobalCore(metaclass=Singleton):
    __core_db: Database

    def init_core_db(self, plugin_names: list):
        data_base_col = {
            "enable": "int",
            "group_id_list": "text"
        }
        self.__core_db = Database()
        if not self.__core_db.init_table(table_name="core", table_key="name",
                                         table_key_type=str, table_col=data_base_col):
            raise Exception("init core table error")
        for plugin_name in plugin_names:
            success, exist = self.__core_db.is_key_exist(plugin_name)
            if not success:
                raise Exception("init core key error")
            if not exist:
                self.__core_db.insert_key(plugin_name)
                self.__core_db.update_value(plugin_name, "enable", 1)
                self.__core_db.update_value(plugin_name, "group_id_list", "[]")

    def is_plugin_enable(self, plugin_name: str, group_id: int, default: bool = True) -> bool:
        success, enable_val = self.__core_db.get_value(plugin_name, "enable")
        if success is False:
            return default
        if enable_val == 0:
            return False

        success, enable_list_val = self.__core_db.get_value(plugin_name, "group_id_list")
        if success is False:
            return default
        if enable_list_val is None:
            return default

        ret, enable_list = JsonUtil.json_str_to_list(enable_list_val)
        if ret is False:
            return default

        if len(enable_list) == 0:
            return True

        if group_id in enable_list:
            return True

        return False

    def get_enable_group(self, plugin_name: str) -> list:
        default = []
        success, enable_val = self.__core_db.get_value(plugin_name, "enable")
        if success is False:
            return default
        if enable_val == 0:
            return default

        success, enable_list_val = self.__core_db.get_value(plugin_name, "group_id_list")
        if success is False:
            return default
        if enable_list_val is None:
            return default

        ret, enable_list = JsonUtil.json_str_to_list(enable_list_val)
        if ret is False:
            return default

        return enable_list

    def get_core_db(self) -> Database:
        return self.__core_db
