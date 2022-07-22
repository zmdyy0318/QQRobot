import pymysql
from pydantic import BaseSettings

from nonebot.log import logger
from nonebot import get_driver

from typing import Union


class Config(BaseSettings):
    maria_host: str
    maria_port: str
    maria_database: str
    maria_user: str
    maria_password: str

    class Config:
        extra = "ignore"


class Database:
    __is_open = False
    __db = None
    __table_name: str
    __table_key: str
    __db_name: str
    __last_error_msg: str

    def __del__(self):
        self.__is_open = False
        if self.__db:
            self.__db.close()

    def init_table(self, table_name: str, table_key: str, table_key_type: type, table_col: dict) -> bool:
        try:
            self.__connect_db()
        except (Exception,) as e:
            logger.error(f"Database::init_table connect error, e={e}")
            self.__last_error_msg = "数据库错误"
            return False

        try:
            self.__create_table(table_name, table_key, table_key_type, table_col)
            if len(table_col):
                self.__insert_col(table_name, table_col)
        except (Exception,) as e:
            logger.error(f"Database::init_table create or update table error, e={e}")
            self.__last_error_msg = "数据库错误"
            return False
        self.__table_name = table_name
        self.__table_key = table_key
        return True

    def connect_table(self, table_name: str):
        ret = False
        try:
            self.__connect_db()
            if self.__table_exist(table_name) is False:
                return False
            self.__table_key = self.__select_table_key(table_name)
            self.__table_name = table_name
            return True
        except (Exception,) as e:
            logger.error(f"Database::connect_table connect error, table_name={table_name}, e={e}")
            self.__last_error_msg = "数据库错误"
            return False

    def get_last_error_msg(self):
        error_msg = self.__last_error_msg
        self.__last_error_msg = ""
        return error_msg

    def is_key_exist(self, key: Union[str, int]) -> (bool, bool):
        ret = False
        exist = False
        cursor = self.__db.cursor()
        try:
            self.__db.ping()
            sql = "SELECT 1 FROM %s WHERE %s = '%s';"
            cursor.execute(sql % (self.__table_name, self.__table_key, key))
            self.__db.commit()
            data = cursor.fetchone()
            if data is not None and data[0] == 1:
                exist = True
            ret = True
        except (Exception,) as e:
            logger.error(f"Database::is_key_exist error, e={e}")
            self.__last_error_msg = "数据库错误"
        cursor.close()
        return ret, exist

    def insert_key(self, key: Union[str, int]) -> bool:
        ret = True
        cursor = self.__db.cursor()
        try:
            self.__db.ping()
            sql = "INSERT INTO %s (%s) VALUES ('%s');"
            cursor.execute(sql % (self.__table_name, self.__table_key, key))
            self.__db.commit()
        except (Exception,) as e:
            logger.error(f"Database::insert_key error, e={e}")
            self.__last_error_msg = "数据库错误"
            self.__db.rollback()
            ret = False
        cursor.close()
        return ret

    def get_value(self, key: Union[str, int], col: str) -> (bool, any):
        ret = False
        val = ""
        cursor = self.__db.cursor()
        try:
            self.__db.ping()
            sql = "SELECT %s FROM %s WHERE %s = '%s';"
            cursor.execute(sql % (col, self.__table_name, self.__table_key, key))
            self.__db.commit()
            data = cursor.fetchone()
            if data is not None and len(data) > 0:
                val = data[0]
            ret = True
        except (Exception,) as e:
            logger.error(f"Database::get_value error, e={e}")
            self.__last_error_msg = "数据库错误"
        cursor.close()
        return ret, val

    def update_value(self, key: Union[str, int], col: str, val: any) -> bool:
        ret = True
        cursor = self.__db.cursor()
        try:
            self.__db.ping()
            sql = "UPDATE %s SET %s = '%s' WHERE %s = '%s';"
            cursor.execute(sql % (self.__table_name, col, val, self.__table_key, key))
            self.__db.commit()
        except (Exception,) as e:
            logger.error(f"Database::update_value error, e={e}")
            self.__last_error_msg = "数据库错误"
            self.__db.rollback()
            ret = False
        cursor.close()
        return ret

    def __connect_db(self) -> None:
        global_config = get_driver().config
        config = Config.parse_obj(global_config)
        host = config.maria_host
        port = int(config.maria_port)
        database = config.maria_database
        user = config.maria_user
        password = config.maria_password
        self.__db = pymysql.connect(host=host, port=port,
                                    user=user, password=password,
                                    database=database)
        self.__db_name = database

    def __create_table(self, table_name: str, table_key: str, table_type: type, table_col: dict) -> None:
        if table_type == str:
            type_str = "VARCHAR(255)"
        elif table_type == int:
            type_str = "INT"
        else:
            raise Exception(f"Database::__create_table error, table_type={table_type}")
        self.__db.ping()
        cursor = self.__db.cursor()
        sql = "CREATE TABLE IF NOT EXISTS %s (%s %s PRIMARY KEY,"
        for key, value in table_col.items():
            sql += "%s %s," % (key, value)
        sql = sql.rstrip(",")
        sql += ");"
        cursor.execute(sql % (table_name, table_key, type_str))
        cursor.close()

    def __insert_col(self, table_name: str, table_col: dict) -> None:
        self.__db.ping()
        cursor = self.__db.cursor()
        sql = "ALTER TABLE %s ADD COLUMN IF NOT EXISTS ("
        for key, value in table_col.items():
            sql += "%s %s," % (key, value)
        sql = sql.rstrip(",")
        sql += ");"
        cursor.execute(sql % table_name)
        cursor.close()

    def __table_exist(self, table_name: str) -> bool:
        self.__db.ping()
        cursor = self.__db.cursor()
        sql = "SELECT * FROM information_schema.tables " \
              "WHERE table_schema = '%s' AND table_name = '%s' " \
              "LIMIT 1;"
        cursor.execute(sql % (self.__db_name, table_name))
        self.__db.commit()
        data = cursor.fetchone()
        cursor.close()
        return data is not None

    def __select_table_key(self, table_name: str) -> str:
        self.__db.ping()
        cursor = self.__db.cursor()
        sql = "SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE " \
              "WHERE table_schema = '%s' AND table_name = '%s' " \
              "LIMIT 1;"
        cursor.execute(sql % (self.__db_name, table_name))
        self.__db.commit()
        data = cursor.fetchone()
        cursor.close()
        return data[0]

