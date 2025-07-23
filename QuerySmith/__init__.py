"""
QuerySmith - Асинхронная ORM библиотека для Python

Поддерживает PostgreSQL и SQLite с единым API.
"""

# Общие классы (новая архитектура)
from .base_model import BaseModel, ColumnModel
from .data_types import DataType, DataTypeFactory, DataTypePG, DataTypeDB

# PostgreSQL классы
from .postgre.base_model import AsyncPGBaseClass
from .postgre.column_model import ColumnModelPG

# SQLite классы  
from .sqlite.base_model import AsyncSQLiteClass
from .sqlite.column_model import ColumnModel as ColumnModelSQLite

# MySQL классы
from .msql.base_model import AsyncMySQLClass as AsyncMySQLClassMySQL
from .msql.column_model import ColumnModelMySQL
from .msql.data_types import DataTypeMySQL

# Обратная совместимость
__all__ = [
    # Общие классы
    'BaseModel',
    'ColumnModel', 
    'DataType',
    'DataTypeFactory',
    
    # PostgreSQL
    'AsyncPGBaseClass',
    'ColumnModelPG',
    'DataTypePG',
    
    # SQLite
    'AsyncSQLiteClass', 
    'ColumnModelSQLite',
    'DataTypeDB',
]

__all__ += [
    'AsyncMySQLClassMySQL',
    'ColumnModelMySQL',
    'DataTypeMySQL',
]

# Версия библиотеки
__version__ = "0.1.0"
