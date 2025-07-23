import json
from typing import List, Dict, Any, Union, Optional
from QuerySmith.base_model import BaseModel, ColumnModel
from QuerySmith.data_types import DataType, DataTypeFactory
import aiomysql
import contextlib
from QuerySmith.query_cache import cache_query

class AsyncMySQLClass(BaseModel):
    """
    MySQL базовый класс для QuerySmith
    Наследует от BaseModel и реализует специфичную для MySQL логику.
    """
    def __init__(self, db_config: Dict[str, Any], table: str):
        super().__init__(table, db_config)
        self.db_config = db_config
        self._setup_columns()
        self._conn: Optional[aiomysql.Connection] = None

    def _setup_columns(self) -> None:
        # Должен быть реализован в дочерних классах
        pass

    def get_attributes(self) -> List[str]:
        # Должен быть реализован в дочерних классах
        return []

    async def _connect(self):
        if self._conn is None or self._conn.closed:
            self._conn = await aiomysql.connect(**self.db_config)
        return self._conn

    async def _execute(self, query: str, params: tuple = None, fetch_one=False, fetch_all=False):
        conn = await self._connect()
        async with conn.cursor() as cur:
            await cur.execute(query, params or ())
            if fetch_one:
                result = await cur.fetchone()
                return result
            elif fetch_all:
                result = await cur.fetchall()
                return result
            else:
                await conn.commit()
                return None

    async def _close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
            await self._conn.wait_closed()

    async def ensure_table_exists(self) -> None:
        try:
            query = f"SHOW TABLES LIKE '{self.table}'"
            conn = await self._connect()
            async with conn.cursor() as cur:
                await cur.execute(query)
                result = await cur.fetchone()
                if not result:
                    schema = self.get_schema_on_create()
                    await cur.execute(schema)
                    await conn.commit()
                    self.create_migration_file(schema)
                    print(f"Таблица {self.table} успешно создана.")
                else:
                    await self._update_table_schema_if_needed(conn)
        except Exception as e:
            print(f"Ошибка при проверке таблицы {self.table}: {e}")
            raise

    async def _update_table_schema_if_needed(self, conn):
        async with conn.cursor() as cur:
            await cur.execute(f"DESCRIBE {self.table}")
            existing_columns = {row[0]: row for row in await cur.fetchall()}
        for column in self.get_list_attributes():
            if column.row_name not in existing_columns:
                alter_query = f"ALTER TABLE {self.table} ADD COLUMN {column.row_name} {column.data_type}"
                async with conn.cursor() as cur:
                    await cur.execute(alter_query)
                    await conn.commit()
                print(f"Добавлена колонка {column.row_name} в таблицу {self.table}")

    async def _insert_data(self, rows_name: List[str], rows_data: List[Any]) -> Any:
        placeholders = ', '.join(['%s'] * len(rows_data))
        query = f'INSERT INTO {self.table} ({', '.join(rows_name)}) VALUES ({placeholders})'
        conn = await self._connect()
        async with conn.cursor() as cur:
            await cur.execute(query, tuple(rows_data))
            await conn.commit()
            return cur.lastrowid

    async def _update_data(self, rows_name: List[str], rows_data: List[Any], id_row: str, id_data: Any) -> Any:
        set_clause = ', '.join(f"{col} = %s" for col in rows_name)
        query = f"UPDATE {self.table} SET {set_clause} WHERE {id_row} = %s"
        params = tuple(rows_data) + (id_data,)
        conn = await self._connect()
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            await conn.commit()
        return id_data

    async def load_one(self, id: Any) -> None:
        query = f'SELECT * FROM {self.table} WHERE id = %s'
        conn = await self._connect()
        async with conn.cursor() as cur:
            await cur.execute(query, (id,))
            result = await cur.fetchone()
            if result:
                data = {}
                table_columns = self.get_list_attributes()
                for idx, column in enumerate(table_columns):
                    value = result[idx]
                    if column.data_type in ('JSON',) and value is not None:
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
        if not kwargs:
            raise ValueError("Необходимо указать хотя бы одно условие")
        conditions = []
        params = []
        for key, value in kwargs.items():
            conditions.append(f"{key} = %s")
            params.append(value)
        where_clause = ' AND '.join(conditions)
        query = f'SELECT * FROM {self.table} WHERE {where_clause}'
        conn = await self._connect()
        async with conn.cursor() as cur:
            await cur.execute(query, tuple(params))
            result = await cur.fetchone()
            if result:
                data = {}
                table_columns = self.get_list_attributes()
                for idx, column in enumerate(table_columns):
                    value = result[idx]
                    if column.data_type in ('JSON',) and value is not None:
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
        table_columns = self.get_list_attributes()
        id_row = next((row.row_name for row in table_columns if row.primary_key), None)
        id_data = next((row.data for row in table_columns if row.primary_key), None)
        if id_row and id_data is not None:
            query = f'DELETE FROM {self.table} WHERE {id_row} = %s'
            conn = await self._connect()
            async with conn.cursor() as cur:
                await cur.execute(query, (id_data,))
                await conn.commit()

    @contextlib.asynccontextmanager
    async def transaction(self):
        conn = await self._connect()
        try:
            await conn.begin()
            yield
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.ensure_closed()

    @classmethod
    async def get_all(cls, db_config: Dict[str, Any], table: str) -> List['AsyncMySQLClass']:
        instance = cls(db_config, table)
        query = f'SELECT * FROM {table}'
        conn = await instance._connect()
        async with conn.cursor() as cur:
            await cur.execute(query)
            results = await cur.fetchall()
            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    table_columns = instance.get_list_attributes()
                    for idx, column in enumerate(table_columns):
                        value = result[idx]
                        if column.data_type in ('JSON',) and value is not None:
                            try:
                                if isinstance(value, str):
                                    value = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                        data[column.row_name] = value
                    await instance.set_results(data)
                    instances.append(instance)
            return instances

    @classmethod
    async def get_all_by(cls, db_config: Dict[str, Any], table: str, **kwargs) -> List['AsyncMySQLClass']:
        instance = cls(db_config, table)
        if not kwargs:
            return await cls.get_all(db_config, table)
        conditions = []
        params = []
        for key, value in kwargs.items():
            conditions.append(f"{key} = %s")
            params.append(value)
        where_clause = ' AND '.join(conditions)
        query = f'SELECT * FROM {table} WHERE {where_clause}'
        conn = await instance._connect()
        async with conn.cursor() as cur:
            await cur.execute(query, tuple(params))
            results = await cur.fetchall()
            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    table_columns = instance.get_list_attributes()
                    for idx, column in enumerate(table_columns):
                        value = result[idx]
                        if column.data_type in ('JSON',) and value is not None:
                            try:
                                if isinstance(value, str):
                                    value = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                        data[column.row_name] = value
                    await instance.set_results(data)
                    instances.append(instance)
            return instances

    @classmethod
    @cache_query()
    async def execute_query(cls, db_config: Dict[str, Any], table: str, query: str) -> List['AsyncMySQLClass']:
        instance = cls(db_config, table)
        conn = await instance._connect()
        async with conn.cursor() as cur:
            await cur.execute(query)
            results = await cur.fetchall()
            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    table_columns = instance.get_list_attributes()
                    for idx, column in enumerate(table_columns):
                        if idx < len(result):
                            value = result[idx]
                            if column.data_type in ('JSON',) and value is not None:
                                try:
                                    if isinstance(value, str):
                                        value = json.loads(value)
                                except json.JSONDecodeError:
                                    pass
                            data[column.row_name] = value
                    await instance.set_results(data)
                    instances.append(instance)
            return instances 