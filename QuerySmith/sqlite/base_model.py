"""
SQLite базовый класс для QuerySmith

Этот модуль содержит специфичную для SQLite реализацию,
наследующую от общего базового класса.
"""

import json
import sqlite3
from typing import List, Dict, Any, Union

import aiosqlite
import contextlib

from QuerySmith.base_model import BaseModel, ColumnModel
from QuerySmith.data_types import DataType, DataTypeFactory
from QuerySmith.query_cache import cache_query


class AsyncSQLiteClass(BaseModel):
    """
    SQLite базовый класс
    
    Наследует от общего BaseModel и реализует специфичную
    для SQLite логику работы с базой данных.
    """
    
    def __init__(self, db_path: str, table: str):
        """
        Инициализация SQLite модели
        
        :param db_path: Путь к файлу базы данных SQLite
        :param table: Название таблицы
        """
        super().__init__(table, db_path)
        self.db_path = db_path
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
        """Подключение к SQLite"""
        return await aiosqlite.connect(database=self.db_path)
    
    async def _execute(self, query: str, params: tuple = None):
        """Выполнение запроса к SQLite"""
        conn = await self._connect()
        try:
            if params:
                result = await conn.execute(query, params)
            else:
                result = await conn.execute(query)
            await conn.commit()
            return result
        finally:
            await conn.close()
    
    async def _close(self):
        """Закрытие соединения с SQLite"""
        # SQLite соединения закрываются автоматически в _execute
        pass
    
    async def ensure_table_exists(self) -> None:
        """Проверяет существование таблицы и создает её при необходимости"""
        try:
            # Проверяем существование таблицы
            query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table}'"
            conn = await self._connect()
            
            try:
                async with conn.execute(query) as cursor:
                    result = await cursor.fetchone()
                
                if not result:
                    # Создаем таблицу
                    schema = self.get_schema_on_create()
                    await conn.execute(schema)
                    await conn.commit()
                    self.create_migration_file(schema)
                    print(f"Таблица {self.table} успешно создана.")
                else:
                    # Проверяем и обновляем схему
                    await self._update_table_schema_if_needed(conn)
                    
            finally:
                await conn.close()
                
        except Exception as e:
            print(f"Ошибка при проверке таблицы {self.table}: {e}")
            raise
    
    async def _update_table_schema_if_needed(self, conn) -> None:
        """Обновляет схему таблицы при необходимости"""
        async with conn.execute(f"PRAGMA table_info({self.table})") as cursor:
            existing_columns = {row[1]: row for row in await cursor.fetchall()}
        
        for column in self.get_list_attributes():
            if column.row_name not in existing_columns:
                # Добавляем новую колонку
                alter_query = f"ALTER TABLE {self.table} ADD COLUMN {column.row_name} {column.data_type}"
                await conn.execute(alter_query)
                await conn.commit()
                print(f"Добавлена колонка {column.row_name} в таблицу {self.table}")
    
    async def _insert_data(self, rows_name: List[str], rows_data: List[Any]) -> Any:
        """Вставляет данные в SQLite"""
        placeholders = ', '.join('?' for _ in rows_data)
        query = f'INSERT INTO {self.table} ({", ".join(rows_name)}) VALUES ({placeholders})'
        
        cursor = await self._execute(query, tuple(rows_data))
        return cursor.lastrowid if cursor else None
    
    async def _update_data(self, rows_name: List[str], rows_data: List[Any], 
                          id_row: str, id_data: Any) -> Any:
        """Обновляет данные в SQLite"""
        set_clause = ', '.join(f"{col} = ?" for col in rows_name)
        query = f"UPDATE {self.table} SET {set_clause} WHERE {id_row} = ?"
        
        params = tuple(rows_data) + (id_data,)
        await self._execute(query, params)
        return id_data
    
    async def load_one(self, id: Any) -> None:
        """Загружает данные из SQLite по ID"""
        query = f'SELECT * FROM {self.table} WHERE id = ?'
        conn = await self._connect()
        
        try:
            async with conn.execute(query, [id]) as cursor:
                result = await cursor.fetchone()
            
            if result:
                data = {}
                table_columns = self.get_list_attributes()
                
                for idx, column in enumerate(table_columns):
                    value = result[idx]
                    # Обработка специальных типов данных
                    if column.data_type == 'BLOB' and value is not None:
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    
                    data[column.row_name] = value
                
                await self.set_results(data)
            else:
                return None
        finally:
            await conn.close()
    
    async def load_one_custom(self, **kwargs) -> None:
        """Загружает данные из SQLite по произвольным условиям (как в PG-классе)"""
        if not kwargs:
            raise ValueError("Необходимо указать хотя бы одно условие")
        
        conditions = []
        params = []
        for key, value in kwargs.items():
            conditions.append(f"{key} = ?")
            params.append(value)
        where_clause = ' AND '.join(conditions)
        query = f'SELECT * FROM {self.table} WHERE {where_clause}'
        conn = await self._connect()
        try:
            async with conn.execute(query, params) as cursor:
                result = await cursor.fetchone()
            if result:
                data = {}
                table_columns = self.get_list_attributes()
                for idx, column in enumerate(table_columns):
                    value = result[idx]
                    if column.data_type == 'BLOB' and value is not None:
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    data[column.row_name] = value
                await self.set_results(data)
            else:
                return None
        finally:
            await conn.close()
    
    async def delete(self) -> None:
        """Удаляет текущий экземпляр из SQLite"""
        table_columns = self.get_list_attributes()
        id_row = next((row.row_name for row in table_columns if row.primary_key), None)
        id_data = next((row.data for row in table_columns if row.primary_key), None)
        
        if id_row and id_data is not None:
            query = f'DELETE FROM {self.table} WHERE {id_row} = ?'
            await self._execute(query, (id_data,))
    
    @contextlib.asynccontextmanager
    async def transaction(self):
        conn = await self._connect()
        try:
            await conn.execute('BEGIN')
            yield
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()
    
    @classmethod
    async def get_all(cls, db_config: str, table: str) -> List['AsyncSQLiteClass']:
        """Возвращает все записи из SQLite"""
        instance = cls(db_config, table)
        query = f'SELECT * FROM {table}'
        
        conn = await instance._connect()
        try:
            async with conn.execute(query) as cursor:
                results = await cursor.fetchall()
            
            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    table_columns = instance.get_list_attributes()
                    
                    for idx, column in enumerate(table_columns):
                        value = result[idx]
                        # Обработка специальных типов данных
                        if column.data_type == 'BLOB' and value is not None:
                            try:
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                        
                        data[column.row_name] = value
                    
                    await instance.set_results(data)
                    instances.append(instance)
            
            return instances
        finally:
            await conn.close()
    
    @classmethod
    async def get_all_by(cls, db_config: str, table: str, **kwargs) -> List['AsyncSQLiteClass']:
        """Возвращает записи из SQLite по условиям (как в PG-классе)"""
        instance = cls(db_config, table)
        if not kwargs:
            return await cls.get_all(db_config, table)
        conditions = []
        params = []
        for key, value in kwargs.items():
            conditions.append(f"{key} = ?")
            params.append(value)
        where_clause = ' AND '.join(conditions)
        query = f'SELECT * FROM {table} WHERE {where_clause}'
        conn = await instance._connect()
        try:
            async with conn.execute(query, params) as cursor:
                results = await cursor.fetchall()
            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    table_columns = instance.get_list_attributes()
                    for idx, column in enumerate(table_columns):
                        value = result[idx]
                        if column.data_type == 'BLOB' and value is not None:
                            try:
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                        data[column.row_name] = value
                    await instance.set_results(data)
                    instances.append(instance)
            return instances
        finally:
            await conn.close()
    
    @classmethod
    @cache_query()
    async def execute_query(cls, db_config: str, table: str, query: str) -> List['AsyncSQLiteClass']:
        instance = cls(db_config, table)
        
        conn = await instance._connect()
        try:
            async with conn.execute(query) as cursor:
                results = await cursor.fetchall()
            
            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    table_columns = instance.get_list_attributes()
                    
                    for idx, column in enumerate(table_columns):
                        if idx < len(result):
                            value = result[idx]
                            # Обработка специальных типов данных
                            if column.data_type == 'BLOB' and value is not None:
                                try:
                                    value = json.loads(value)
                                except json.JSONDecodeError:
                                    pass
                            
                            data[column.row_name] = value
                    
                    await instance.set_results(data)
                    instances.append(instance)
            
            return instances
        finally:
            await conn.close()
