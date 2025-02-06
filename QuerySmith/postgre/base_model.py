import json
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List

import asyncpg
import asyncio
import os

from asyncpg import Record

from QuerySmith.postgre.column_model import ColumnModel
from QuerySmith.postgre.data_types import DataTypeDB


class AsyncPGBaseClass(ABC):
    def __init__(self, db_config, table, max_retries=5, retry_delay=2):
        self.db_config = db_config
        self.conn = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.table = table

    @abstractmethod
    def get_attributes(self):
        """Метод, который должен возвращать список имён атрибутов, заданных в дочернем классе."""
        pass

    async def set_results(self, results):
        """Метод, для сохранения данных в классе таблицы."""
        for attr, data in results.items():
            setattr(self, attr, data)

    def get_list_attributes(self) -> List['ColumnModel']:
        """Возвращает список атрибутов дочернего класса"""
        return [getattr(self, attr) for attr in self.get_attributes()]

    def get_schema_on_create(self) -> str:
        """Создает sql-схему для создания таблицы"""
        table_rows = self.get_list_attributes()
        references = ''
        schema = f'CREATE TABLE {self.table} (\n'
        for row in table_rows:

            if row.primary_key:
                primary_key = ' PRIMARY KEY'
            else:
                primary_key = ''

            if row.unique:
                unique = ' UNIQUE'
            else:
                unique = ''

            if row.references_table:
                reference_table_rows = row.references_table.get_list_attributes()
                reference = None
                for ref_row in reference_table_rows:
                    if ref_row.primary_key:
                        reference = f'FOREIGN KEY ({row.row_name}) REFERENCES {row.references_table.table}({ref_row.row_name})\n'
                        references += reference
                        break
                if not reference:
                    raise 'The reference table does not have a primary key!'

            schema += f'{row.row_name} {row.data_type}{primary_key}{unique}\n'

        schema += references
        schema += ')'

    def create_migration_file(self, schema: str):
        """
        Создаёт файл миграции для таблицы.

        :param schema: SQL-схема для создания таблицы.
        """

        migrations_dir = "./migrations_postgre"
        os.makedirs(migrations_dir, exist_ok=True)

        migration_filename = f"{migrations_dir}/create_{self.table}_{datetime.now().timestamp()}.sql"
        if not os.path.exists(migration_filename):
            with open(migration_filename, "w", encoding="utf-8") as migration_file:
                migration_file.write(f"-- Миграция для создания таблицы {self.table}\n")
                migration_file.write(schema)
            print(f"Файл миграции '{migration_filename}' успешно создан.")
        else:
            print(f"Файл миграции '{migration_filename}' уже существует.")

    async def connect(self) -> None:
        """Подключается к базе данных с повторными попытками в случае неудачи."""
        attempt = 0
        while attempt < self.max_retries:
            try:
                self.conn = await asyncpg.connect(**self.db_config)
                print("Соединение установлено.")
                break
            except (asyncpg.exceptions.ConnectionDoesNotExistError, OSError):
                attempt += 1
                print(f"Попытка {attempt}/{self.max_retries} не удалась. Повтор через {self.retry_delay} секунд.")
                await asyncio.sleep(self.retry_delay)
        else:
            raise ConnectionError("Не удалось установить соединение с базой данных после нескольких попыток.")

    async def reconnect_if_needed(self) -> None:
        """Проверяет соединение и переподключается, если соединение было потеряно."""
        if self.conn is None or self.conn.is_closed():
            print("Соединение потеряно. Переподключение...")
            await self.connect()

    async def execute(self, query, *params, fetch_one=False, fetch_all=False) -> None | Record | List['Record']:
        """Выполняет SQL-запрос с поддержкой возврата данных и автоматическим переподключением."""
        attempt = 0
        while attempt < self.max_retries:
            try:
                await self.reconnect_if_needed()
                if fetch_one:
                    return await self.conn.fetchrow(query, *params)
                elif fetch_all:
                    return await self.conn.fetch(query, *params)
                else:
                    await self.conn.execute(query, *params)
                break
            except (asyncpg.exceptions.ConnectionDoesNotExistError, asyncpg.exceptions.InterfaceError, OSError) as e:
                print(f"Ошибка выполнения запроса: {e}. Попытка повторного подключения.")
                attempt += 1
                await self.connect()
                await asyncio.sleep(self.retry_delay)
        else:
            raise ConnectionError("The request failed after several attempts.")

    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self.conn is not None and not self.conn.is_closed():
            await self.conn.close()
            print("Соединение закрыто.")

    async def ensure_table_exists(self) -> None:
        """
        Проверяет, существует ли таблица, и создаёт её, если не существует.
        """
        await self.connect()
        try:
            query = f"""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = $1
            )
            """
            table_exists = await self.conn.fetchval(query, self.table)

            if not table_exists:

                schema = self.get_schema_on_create()

                await self.conn.execute(schema)
                print(f"Таблица '{self.table}' была успешно создана.")
                self.create_migration_file(schema)
            else:
                print(f"Таблица '{self.table}' уже существует.")
        finally:
            await self.close()

    async def save(self):
        """Сохраняет текущий экземпляр в базе данных."""
        try:
            await self.connect()

            table_columns = self.get_list_attributes()

            id_row = None
            id_index = None

            index = 1

            rows_name = []
            rows_data = []
            rows_index = []

            for row in table_columns:
                if row.primary_key:
                    id_row = row.row_name
                    continue

                if row.data_type == DataTypeDB.json or row.data_type == DataTypeDB.jsonb:
                    rows_data.append(json.dumps(row.data))
                else:
                    rows_data.append(row.data)

                rows_name.append(row.row_name)
                rows_index.append(f'${index}')
                index += 1

            if id_row:
                id_index = f'${index}'

            if id_row is None:
                query = (
                    f"INSERT INTO {self.table} ({', '.join(rows_name)}) VALUES "
                    f"({', '.join(rows_index)}) RETURNING {id_row}")
                result = await self.execute(
                    query,
                    rows_data,
                    fetch_one=True
                )
                if result:
                    return result['id_row']
                else:
                    raise 'Failed to make record'
            else:
                await self.execute(
                    f"UPDATE {self.table} SET ({', '.join(rows_name)}) VALUES ({', '.join(rows_index)}) WHERE {id_row} = {id_index}",
                    rows_data
                )
        finally:
            await self.close()

    async def load_one(self, id) -> None:
        """Загружает данные из базы данных в текущий экземпляр."""
        try:
            await self.connect()

            table_columns = self.get_list_attributes()

            query = f"SELECT * FROM {self.table} WHERE id = $1"
            result = await self.execute(query, id, fetch_one=True)
            if result:
                data = {}
                for column in table_columns:
                    if column.data_type == DataTypeDB.json or column.data_type == DataTypeDB.jsonb:
                        data[column.row_name] = json.loads(result[column.row_name])
                    else:
                        data[column.row_name] = result[column.row_name]
                await self.set_results(results=data)
            else:
                raise 'The record was not found'
        finally:
            await self.close()

    async def delete(self) -> None:
        """Удаляет текущий экземпляр из базы данных."""
        try:
            await self.connect()

            table_columns = self.get_list_attributes()

            id_row = next((row.row_name for row in table_columns if row.primary_key), None)
            data_row = next((row.data for row in table_columns if row.primary_key), None)

            if id_row is not None:
                await self.execute(f"DELETE FROM {self.table} WHERE {id_row} = $1", data_row)
        finally:
            await self.close()

    @classmethod
    async def get_all(cls, db_config, table) -> List['AsyncPGBaseClass']:
        """
        Возвращает все записи из базы данных как список объектов.
        """
        instance = cls(db_config, table)
        try:
            await instance.connect()

            table_columns = instance.get_list_attributes()

            query = "SELECT * FROM users"
            results = await instance.execute(query, fetch_all=True)

            instances = []
            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}
                    for column in table_columns:
                        if column.data_type == DataTypeDB.json or column.data_type == DataTypeDB.jsonb:
                            data[column.row_name] = json.loads(result[column.row_name])
                        else:
                            data[column.row_name] = result[column.row_name]
                    await instance.set_results(data)
                    instances.append(instance)

                return instances
            else:
                return None
        finally:
            await instance.close()
