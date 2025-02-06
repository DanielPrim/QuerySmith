import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

import aiosqlite

from QuerySmith.sqlite.column_model import ColumnModel


class AsyncSQLiteClass(ABC):
    # todo: от сюда
    def __init__(self, db_path, table):
        self.db_path = db_path
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

        migrations_dir = "./migrations_sqlite"
        os.makedirs(migrations_dir, exist_ok=True)

        migration_filename = f"{migrations_dir}/create_{self.table}_{datetime.now().timestamp()}.sql"
        if not os.path.exists(migration_filename):
            with open(migration_filename, "w", encoding="utf-8") as migration_file:
                migration_file.write(f"-- Миграция для создания таблицы {self.table}\n")
                migration_file.write(schema)
            print(f"Файл миграции '{migration_filename}' успешно создан.")
        else:
            print(f"Файл миграции '{migration_filename}' уже существует.")

    # todo: и до сюда можно спокойно вынести в один класс

    async def ensure_table_exists(self):
        """
        Проверяет, существует ли таблица, и создаёт её, если не существует.
        """
        # Проверяем, существует ли таблица
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table}'"
        conn = await aiosqlite.connect(database=self.db_path)
        try:
            async with conn.execute(query) as cursor:
                result = await cursor.fetchone()

            if not result:
                schema = self.get_schema_on_create()
                await conn.execute(schema)
                await conn.commit()
                self.create_migration_file(schema)
                print(f"Таблица {self.table} успешно создана.")
            else:
                async with conn.execute(f"PRAGMA table_info({self.table})") as cursor:
                    existing_columns = {row[1]: row for row in await cursor.fetchall()}

                for column in self.get_list_attributes():
                    if column.row_name not in existing_columns:
                        alter_query = f"ALTER TABLE {self.table} ADD COLUMN {column.row_name} {column.data_type}"
                        await conn.execute(alter_query)
                        await conn.commit()

                print(f"Проверка и обновление таблицы {self.table} завершены.")
        finally:
            await conn.close()

    async def save(self):
        """Сохраняет текущий экземпляр в базе данных."""
        conn = await aiosqlite.connect(database=self.db_path)
        try:

            table_columns = self.get_list_attributes()

            id_row = None
            id_data = None

            rows_name = []
            rows_data = []
            rows_index = []

            for row in table_columns:
                if row.primary_key:
                    id_row = row.row_name
                    id_data = row.data

                # if row.data_type == DataTypeDB.json or row.data_type == DataTypeDB.jsonb:
                #     rows_data.append(json.dumps(row.data))
                # else:
                #     rows_data.append(row.data)

                rows_data.append(row.data)

                rows_name.append(row.row_name)
                rows_index.append(f'?, ')

            if id_row:
                cursor = await conn.execute(f'INSERT INTO {self.table} ({', '.join(rows_name)}) VALUES ({', '.join(rows_index)})', rows_data)
                await conn.commit()
                await cursor.close()

            else:
                rows_data.append(id_data)
                cursor = await conn.execute(f'UPDATE {self.table} SET ({', '.join(rows_name)}) VALUES ({', '.join(rows_index)}) WHERE {id_row} = ?', rows_data)
                await conn.commit()
                await cursor.close()
        finally:
            await conn.close()

    async def load_one(self, id) -> None:
        """Загружает данные из базы данных в текущий экземпляр."""
        conn = await aiosqlite.connect(database=self.db_path)
        try:
            cursor = await conn.execute(f'SELECT * FROM {self.table} WHERE id = ?', [id])
            result = await cursor.fetchone()
            await cursor.close()
            if result:
                data = {}
                table_columns = self.get_list_attributes()

                for idx, column in enumerate(table_columns):
                    data[column.row_name] = result[idx]
                await self.set_results(results=data)
            else:
                raise 'The record was not found'
        finally:
            await conn.close()

    async def delete(self) -> None:
        """Удаляет текущий экземпляр из базы данных."""
        conn = await aiosqlite.connect(database=self.db_path)
        try:

            table_columns = self.get_list_attributes()

            id_row = next((row.row_name for row in table_columns if row.primary_key), None)
            data_row = next((row.data for row in table_columns if row.primary_key), None)

            cursor = await conn.execute(f'DELETE FROM {self.table} WHERE {id_row} = ?', [data_row])
            await conn.commit()
            await cursor.close()
        finally:
            await conn.close()

    @classmethod
    async def get_all(cls, db_config, table) -> List['AsyncSQLiteClass']:
        """
        Возвращает все записи из базы данных как список объектов.
        """
        instance = cls(db_config, table)
        conn = await aiosqlite.connect(database=instance.db_path)
        try:
            table_columns = instance.get_list_attributes()
            instances = []

            cursor = await conn.execute(f'SELECT * FROM {instance.table}')
            results = await cursor.fetchall()

            if results:
                for result in results:
                    instance = cls(db_config, table)
                    data = {}

                    for idx, column in enumerate(table_columns):
                        data[column.row_name] = result[idx]
                    await instance.set_results(results=data)
                    instances.append(instance)
                return instances
            else:
                return None
        finally:
            await conn.close()
