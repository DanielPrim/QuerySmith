"""
PostgreSQL базовый класс для QuerySmith

Этот модуль содержит специфичную для PostgreSQL реализацию,
наследующую от общего базового класса.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

import asyncpg
import asyncio

from asyncpg import Record

from QuerySmith.base_model import BaseModel, ColumnModel
from QuerySmith.data_types import DataType, DataTypeFactory
from QuerySmith.query_cache import cache_query


class AsyncPGBaseClass(BaseModel):
    """
    PostgreSQL базовый класс
    
    Наследует от общего BaseModel и реализует специфичную
    для PostgreSQL логику работы с базой данных.
    """
    
    def __init__(self, db_config: Dict[str, Any], table: str, 
                 max_retries: int = 5, retry_delay: int = 2):
        """
        Инициализация PostgreSQL модели
        
        :param db_config: Конфигурация PostgreSQL
        :param table: Название таблицы
        :param max_retries: Максимальное количество попыток подключения
        :param retry_delay: Задержка между попытками подключения
        """
        super().__init__(table, db_config)
        self.conn = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._setup_columns()
    
    def _setup_columns(self) -> None:
        """
        Настройка столбцов модели.
        Должен быть переопределен в дочерних классах.
        """
        # Этот метод будет переопределен в дочерних классах
        pass
    
    def get_attributes(self) -> List[str]:
        """
        Возвращает список имен атрибутов модели.
        Должен быть переопределен в дочерних классах.
        """
        # Этот метод будет переопределен в дочерних классах
        return []
    
    async def _connect(self):
        """Подключение к PostgreSQL"""
        if self.conn is None or self.conn.is_closed():
            for attempt in range(self.max_retries):
                try:
                    self.conn = await asyncpg.connect(**self.db_config)
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep(self.retry_delay)
    
    async def _execute(self, query: str, params: tuple = None, 
                      fetch_one: bool = False, fetch_all: bool = False):
        """Выполнение запроса к PostgreSQL"""
        await self._connect()
        
        try:
            if params:
                result = await self.conn.execute(query, *params)
            else:
                result = await self.conn.execute(query)
            
            if fetch_one:
                return await self.conn.fetchrow(query, *params) if params else await self.conn.fetchrow(query)
            elif fetch_all:
                return await self.conn.fetch(query, *params) if params else await self.conn.fetch(query)
            else:
                return result
        except Exception as e:
            await self._close()
            raise e
    
    async def _close(self):
        """Закрытие соединения с PostgreSQL"""
        if self.conn and not self.conn.is_closed():
            await self.conn.close()
    
    async def ensure_table_exists(self) -> None:
        """Проверяет существование таблицы и создает её при необходимости"""
        try:
            # Проверяем существование таблицы
            query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
            """
            result = await self._execute(query, (self.table,), fetch_one=True)
            
            if not result[0]:
                # Создаем таблицу
                schema = self.get_schema_on_create()
                await self._execute(schema)
                self.create_migration_file(schema)
                print(f"Таблица {self.table} успешно создана.")
            else:
                # Проверяем и обновляем схему
                await self._update_table_schema_if_needed()
                
        except Exception as e:
            print(f"Ошибка при проверке таблицы {self.table}: {e}")
            raise
    
    async def _update_table_schema_if_needed(self) -> None:
        """Обновляет схему таблицы при необходимости"""
        current_schema = await self._get_current_table_schema()
        expected_columns = self.get_list_attributes()
        
        for column in expected_columns:
            if column.row_name not in current_schema:
                # Добавляем новую колонку
                alter_query = f"ALTER TABLE {self.table} ADD COLUMN {column.row_name} {column.data_type}"
                await self._execute(alter_query)
                print(f"Добавлена колонка {column.row_name} в таблицу {self.table}")
    
    async def _get_current_table_schema(self) -> Dict[str, Dict]:
        """Получает текущую схему таблицы"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = $1
        """
        rows = await self._execute(query, (self.table,), fetch_all=True)
        
        schema = {}
        for row in rows:
            schema[row['column_name']] = {
                'data_type': row['data_type'],
                'is_nullable': row['is_nullable'] == 'YES',
                'default': row['column_default']
            }
        return schema
    
    async def _insert_data(self, rows_name: List[str], rows_data: List[Any]) -> Any:
        """Вставляет данные в PostgreSQL"""
        placeholders = ', '.join(f'${i+1}' for i in range(len(rows_data)))
        query = f'INSERT INTO {self.table} ({", ".join(rows_name)}) VALUES ({placeholders}) RETURNING id'
        
        result = await self._execute(query, tuple(rows_data), fetch_one=True)
        return result['id'] if result else None
    
    async def _update_data(self, rows_name: List[str], rows_data: List[Any], 
                          id_row: str, id_data: Any) -> Any:
        """Обновляет данные в PostgreSQL"""
        set_clause = ', '.join(f"{col} = ${i+1}" for i, col in enumerate(rows_name))
        query = f"UPDATE {self.table} SET {set_clause} WHERE {id_row} = ${len(rows_data)+1}"
        
        params = tuple(rows_data) + (id_data,)
        result = await self._execute(query, params)
        return id_data
    
    async def load_one(self, id: Any) -> None:
        """Загружает данные из PostgreSQL по ID"""
        query = f'SELECT * FROM {self.table} WHERE id = $1'
        result = await self._execute(query, (id,), fetch_one=True)
        
        if result:
            data = {}
            table_columns = self.get_list_attributes()
            
            for idx, column in enumerate(table_columns):
                value = result[idx]
                # Обработка специальных типов данных
                if column.data_type in ('JSON', 'JSONB') and value is not None:
                    try:
                        if isinstance(value, str):
                            value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                
                data[column.row_name] = value
            
            await self.set_results(data)
        else:
            return None
    
    async def load_one_custom(self, **kwargs) -> None:
        """Загружает данные из PostgreSQL по произвольным условиям"""
        if not kwargs:
            raise ValueError("Необходимо указать хотя бы одно условие")
        
        conditions = []
        params = []
        param_index = 1
        
        for key, value in kwargs.items():
            conditions.append(f"{key} = ${param_index}")
            params.append(value)
            param_index += 1
        
        where_clause = ' AND '.join(conditions)
        query = f'SELECT * FROM {self.table} WHERE {where_clause}'
        
        result = await self._execute(query, tuple(params), fetch_one=True)
        
        if result:
            data = {}
            table_columns = self.get_list_attributes()
            
            for idx, column in enumerate(table_columns):
                value = result[idx]
                # Обработка специальных типов данных
                if column.data_type in ('JSON', 'JSONB') and value is not None:
                    try:
                        if isinstance(value, str):
                            value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                
                data[column.row_name] = value
            
            await self.set_results(data)
        else:
            return None
    
    async def delete(self) -> None:
        """Удаляет текущий экземпляр из PostgreSQL"""
        table_columns = self.get_list_attributes()
        id_row = next((row.row_name for row in table_columns if row.primary_key), None)
        id_data = next((row.data for row in table_columns if row.primary_key), None)
        
        if id_row and id_data is not None:
            query = f'DELETE FROM {self.table} WHERE {id_row} = $1'
            await self._execute(query, (id_data,))
    
    async def transaction(self):
        await self._connect()
        return self.conn.transaction()
    
    @classmethod
    async def get_all(cls, db_config: Dict[str, Any], table: str) -> List['AsyncPGBaseClass']:
        """Возвращает все записи из PostgreSQL"""
        instance = cls(db_config, table)
        query = f'SELECT * FROM {table}'
        
        results = await instance._execute(query, fetch_all=True)
        instances = []
        
        if results:
            for result in results:
                instance = cls(db_config, table)
                data = {}
                table_columns = instance.get_list_attributes()
                
                for idx, column in enumerate(table_columns):
                    value = result[idx]
                    # Обработка специальных типов данных
                    if column.data_type in ('JSON', 'JSONB') and value is not None:
                        try:
                            if isinstance(value, str):
                                value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    
                    data[column.row_name] = value
                
                await instance.set_results(data)
                instances.append(instance)
        
        await instance._close()
        return instances
    
    @classmethod
    async def get_all_by(cls, db_config: Dict[str, Any], table: str, 
                        **kwargs) -> List['AsyncPGBaseClass']:
        """Возвращает записи из PostgreSQL по условиям"""
        if not kwargs:
            return await cls.get_all(db_config, table)
        
        instance = cls(db_config, table)
        conditions = []
        params = []
        param_index = 1
        
        for key, value in kwargs.items():
            conditions.append(f"{key} = ${param_index}")
            params.append(value)
            param_index += 1
        
        where_clause = ' AND '.join(conditions)
        query = f'SELECT * FROM {table} WHERE {where_clause}'
        
        results = await instance._execute(query, tuple(params), fetch_all=True)
        instances = []
        
        if results:
            for result in results:
                instance = cls(db_config, table)
                data = {}
                table_columns = instance.get_list_attributes()
                
                for idx, column in enumerate(table_columns):
                    value = result[idx]
                    # Обработка специальных типов данных
                    if column.data_type in ('JSON', 'JSONB') and value is not None:
                        try:
                            if isinstance(value, str):
                                value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    
                    data[column.row_name] = value
                
                await instance.set_results(data)
                instances.append(instance)
        
        await instance._close()
        return instances
    
    @classmethod
    @cache_query()
    async def execute_query(cls, db_config: Dict[str, Any], table: str, query: str) -> List['AsyncPGBaseClass']:
        instance = cls(db_config, table)
        results = await instance._execute(query, fetch_all=True)
        instances = []
        if results:
            for result in results:
                instance = cls(db_config, table)
                data = {}
                table_columns = instance.get_list_attributes()
                for idx, column in enumerate(table_columns):
                    if idx < len(result):
                        value = result[idx]
                        if column.data_type in ('JSON', 'JSONB') and value is not None:
                            try:
                                if isinstance(value, str):
                                    value = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                        data[column.row_name] = value
                await instance.set_results(data)
                instances.append(instance)
        await instance._close()
        return instances
