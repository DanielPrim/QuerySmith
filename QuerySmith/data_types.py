"""
Общие типы данных для QuerySmith

Этот модуль содержит универсальные типы данных, которые работают
с разными базами данных (PostgreSQL, SQLite).
"""

from enum import Enum
from typing import Optional, List


class DataType(Enum):
    """Универсальные типы данных для всех БД"""
    
    # Строковые типы
    TEXT = "TEXT"
    CHAR = "CHAR"
    VARCHAR = "VARCHAR"
    
    # Числовые типы
    INTEGER = "INTEGER"
    SMALLINT = "SMALLINT"
    BIGINT = "BIGINT"
    REAL = "REAL"
    DECIMAL = "DECIMAL"
    SERIAL = "SERIAL"
    
    # Временные типы
    TIMESTAMP = "TIMESTAMP"
    DATE = "DATE"
    TIME = "TIME"
    INTERVAL = "INTERVAL"
    
    # Логические типы
    BOOLEAN = "BOOLEAN"
    
    # Бинарные типы
    BLOB = "BLOB"
    BYTEA = "BYTEA"
    
    # JSON типы
    JSON = "JSON"
    JSONB = "JSONB"
    
    def get_sql_type(self, db_type: str, length: Optional[int] = None) -> str:
        """
        Возвращает SQL тип для конкретной БД
        
        :param db_type: Тип БД ('postgresql' или 'sqlite')
        :param length: Длина для типов с переменной длиной
        :return: SQL тип данных
        """
        if db_type == "postgresql":
            return self._get_postgresql_type(length)
        elif db_type == "sqlite":
            return self._get_sqlite_type(length)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _get_postgresql_type(self, length: Optional[int] = None) -> str:
        """Возвращает PostgreSQL тип данных"""
        type_mapping = {
            DataType.TEXT: "TEXT",
            DataType.CHAR: f"CHAR({length or 1})",
            DataType.VARCHAR: f"VARCHAR({length or 255})",
            DataType.INTEGER: "INTEGER",
            DataType.SMALLINT: "SMALLINT",
            DataType.BIGINT: "BIGINT",
            DataType.REAL: "REAL",
            DataType.DECIMAL: "DECIMAL",
            DataType.SERIAL: "SERIAL",
            DataType.TIMESTAMP: "TIMESTAMP",
            DataType.DATE: "DATE",
            DataType.TIME: "TIME",
            DataType.INTERVAL: "INTERVAL",
            DataType.BOOLEAN: "BOOLEAN",
            DataType.BLOB: "BYTEA",
            DataType.BYTEA: "BYTEA",
            DataType.JSON: "JSON",
            DataType.JSONB: "JSONB",
        }
        
        sql_type = type_mapping.get(self, self.value)
        
        # Обработка типов с длиной
        if self in (DataType.CHAR, DataType.VARCHAR) and length is None:
            raise ValueError(f"Length must be specified for {self.value}")
        
        return sql_type
    
    def _get_sqlite_type(self, length: Optional[int] = None) -> str:
        """Возвращает SQLite тип данных"""
        type_mapping = {
            DataType.TEXT: "TEXT",
            DataType.CHAR: "TEXT",  # SQLite не поддерживает CHAR, используем TEXT
            DataType.VARCHAR: "TEXT",  # SQLite не поддерживает VARCHAR, используем TEXT
            DataType.INTEGER: "INTEGER",
            DataType.SMALLINT: "INTEGER",  # SQLite не поддерживает SMALLINT
            DataType.BIGINT: "INTEGER",  # SQLite не поддерживает BIGINT
            DataType.REAL: "REAL",
            DataType.DECIMAL: "REAL",  # SQLite не поддерживает DECIMAL
            DataType.SERIAL: "INTEGER",  # SQLite не поддерживает SERIAL
            DataType.TIMESTAMP: "TEXT",  # SQLite хранит как TEXT
            DataType.DATE: "TEXT",  # SQLite хранит как TEXT
            DataType.TIME: "TEXT",  # SQLite хранит как TEXT
            DataType.INTERVAL: "TEXT",  # SQLite не поддерживает INTERVAL
            DataType.BOOLEAN: "INTEGER",  # SQLite хранит как INTEGER (0/1)
            DataType.BLOB: "BLOB",
            DataType.BYTEA: "BLOB",  # SQLite не поддерживает BYTEA
            DataType.JSON: "TEXT",  # SQLite хранит JSON как TEXT
            DataType.JSONB: "TEXT",  # SQLite не поддерживает JSONB
        }
        
        return type_mapping.get(self, self.value)


class DataTypeFactory:
    """Фабрика для создания типов данных"""
    
    @staticmethod
    def create_column_type(data_type: DataType, db_type: str, 
                          length: Optional[int] = None) -> str:
        """
        Создает SQL тип для столбца
        
        :param data_type: Тип данных
        :param db_type: Тип БД
        :param length: Длина (для VARCHAR, CHAR)
        :return: SQL тип данных
        """
        return data_type.get_sql_type(db_type, length)
    
    @staticmethod
    def get_supported_types(db_type: str) -> List[DataType]:
        """
        Возвращает список поддерживаемых типов для БД
        
        :param db_type: Тип БД
        :return: Список поддерживаемых типов
        """
        if db_type == "postgresql":
            return [
                DataType.TEXT, DataType.CHAR, DataType.VARCHAR,
                DataType.INTEGER, DataType.SMALLINT, DataType.BIGINT,
                DataType.REAL, DataType.DECIMAL, DataType.SERIAL,
                DataType.TIMESTAMP, DataType.DATE, DataType.TIME, DataType.INTERVAL,
                DataType.BOOLEAN, DataType.BYTEA, DataType.JSON, DataType.JSONB
            ]
        elif db_type == "sqlite":
            return [
                DataType.TEXT, DataType.INTEGER, DataType.REAL,
                DataType.TIMESTAMP, DataType.DATE, DataType.TIME,
                DataType.BOOLEAN, DataType.BLOB, DataType.JSON
            ]
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    @staticmethod
    def validate_type(data_type: DataType, db_type: str) -> bool:
        """
        Проверяет, поддерживается ли тип данных в БД
        
        :param data_type: Тип данных
        :param db_type: Тип БД
        :return: True если тип поддерживается
        """
        supported_types = DataTypeFactory.get_supported_types(db_type)
        return data_type in supported_types


# Обратная совместимость с существующими классами
class DataTypePG:
    """Совместимость с PostgreSQL типами"""
    TEXT = DataType.TEXT
    CHAR = DataType.CHAR
    VARCHAR = DataType.VARCHAR
    SMALLINT = DataType.SMALLINT
    INTEGER = DataType.INTEGER
    BIGINT = DataType.BIGINT
    DECIMAL = DataType.DECIMAL
    REAL = DataType.REAL
    SERIAL = DataType.SERIAL
    TIMESTAMP = DataType.TIMESTAMP
    DATE = DataType.DATE
    TIME = DataType.TIME
    INTERVAL = DataType.INTERVAL
    BOOLEAN = DataType.BOOLEAN
    BYTEA = DataType.BYTEA
    JSON = DataType.JSON
    JSONB = DataType.JSONB


class DataTypeDB:
    """Совместимость с SQLite типами"""
    TEXT = DataType.TEXT
    INTEGER = DataType.INTEGER
    REAL = DataType.REAL
    TIMESTAMP = DataType.TIMESTAMP
    DATE = DataType.DATE
    TIME = DataType.TIME
    INTERVAL = DataType.INTERVAL
    BOOLEAN = DataType.BOOLEAN
    BLOB = DataType.BLOB 