"""
Общий базовый класс для QuerySmith

Этот модуль содержит общий базовый класс, который устраняет дублирование кода
между PostgreSQL и SQLite модулями.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class ColumnModel:
    """Общая модель столбца для всех типов БД"""
    data: Any
    row_name: str
    data_type: str
    primary_key: bool = False
    unique: bool = False
    references_table: Optional['BaseModel'] = None
    len_data_type: Optional[int] = None


class BaseModel(ABC):
    """
    Общий базовый класс для всех моделей QuerySmith
    
    Этот класс содержит общую логику для работы с базами данных,
    устраняя дублирование кода между PostgreSQL и SQLite модулями.
    """
    
    def __init__(self, table: str, db_config: Union[str, Dict[str, Any]]):
        """
        Инициализация базовой модели
        
        :param table: Название таблицы
        :param db_config: Конфигурация БД (строка пути для SQLite, словарь для PostgreSQL)
        """
        self.table = table
        self.db_config = db_config
        self._columns: Dict[str, ColumnModel] = {}
        self._setup_columns()
    
    @abstractmethod
    def _setup_columns(self) -> None:
        """
        Абстрактный метод для настройки столбцов модели.
        Должен быть реализован в дочерних классах.
        """
        pass
    
    @abstractmethod
    def get_attributes(self) -> List[str]:
        """
        Возвращает список имен атрибутов модели.
        Должен быть реализован в дочерних классах.
        """
        pass
    
    @abstractmethod
    async def _connect(self):
        """Абстрактный метод для подключения к БД"""
        pass
    
    @abstractmethod
    async def _execute(self, query: str, params: tuple = None):
        """Абстрактный метод для выполнения запросов"""
        pass
    
    @abstractmethod
    async def _close(self):
        """Абстрактный метод для закрытия соединения"""
        pass
    
    @abstractmethod
    async def transaction(self):
        """Асинхронный контекстный менеджер транзакции"""
        pass
    
    def get_list_attributes(self) -> List[ColumnModel]:
        """Возвращает список атрибутов модели"""
        return [getattr(self, attr) for attr in self.get_attributes()]
    
    def get_schema_on_create(self) -> str:
        """Создает SQL-схему для создания таблицы"""
        table_rows = self.get_list_attributes()
        references = []
        schema = f'CREATE TABLE {self.table} (\n'
        
        row_definitions = []
        
        for row in table_rows:
            constraints = []
            
            if row.primary_key:
                constraints.append('PRIMARY KEY')
            
            if row.unique:
                constraints.append('UNIQUE')
            
            row_definitions.append(f'{row.row_name} {row.data_type} {" ".join(constraints)}')
            
            if row.references_table:
                reference_table_rows = row.references_table.get_list_attributes()
                reference = None
                for ref_row in reference_table_rows:
                    if ref_row.primary_key:
                        reference = f'FOREIGN KEY ({row.row_name}) REFERENCES {row.references_table.table}({ref_row.row_name})'
                        references.append(reference)
                        break
                if not reference:
                    raise ValueError('The reference table does not have a primary key!')
        
        schema += ',\n'.join(row_definitions)
        if references:
            schema += ',\n' + ',\n'.join(references)
        schema += '\n);'
        
        return schema
    
    def create_migration_file(self, schema: str, alter_schema: Optional[str] = None) -> str:
        """
        Создает файл миграции для таблицы
        
        :param schema: SQL-схема для создания таблицы
        :param alter_schema: SQL-запрос для изменения таблицы (если есть)
        :return: Путь к созданному файлу миграции
        """
        db_type = self._get_db_type()
        migrations_dir = f"./migrations_{db_type}"
        os.makedirs(migrations_dir, exist_ok=True)
        
        timestamp = datetime.now().timestamp()
        if alter_schema:
            migration_filename = f"{migrations_dir}/alter_{self.table}_{timestamp}.sql"
            content = f"-- Миграция для изменения таблицы {self.table}\n{alter_schema}"
        else:
            migration_filename = f"{migrations_dir}/create_{self.table}_{timestamp}.sql"
            content = f"-- Миграция для создания таблицы {self.table}\n{schema}"
        
        if not os.path.exists(migration_filename):
            with open(migration_filename, "w", encoding="utf-8") as migration_file:
                migration_file.write(content)
            print(f"Файл миграции '{migration_filename}' успешно создан.")
        else:
            print(f"Файл миграции '{migration_filename}' уже существует.")
        
        return migration_filename
    
    def _get_db_type(self) -> str:
        """Определяет тип базы данных по конфигурации"""
        if isinstance(self.db_config, str):
            return "sqlite"
        else:
            return "postgre"
    
    async def set_results(self, results: Dict[str, Any]) -> None:
        """Сохраняет результаты запроса в модель"""
        for attr, data in results.items():
            if hasattr(self, attr):
                column = getattr(self, attr)
                if hasattr(column, 'data'):
                    column.data = data
                else:
                    setattr(self, attr, data)
    
    async def ensure_table_exists(self) -> None:
        """Проверяет существование таблицы и создает её при необходимости"""
        # Этот метод будет переопределен в дочерних классах
        # для специфичной логики каждой БД
        pass
    
    async def save(self) -> Any:
        """Сохраняет текущий экземпляр в базу данных"""
        await self.ensure_table_exists()
        
        table_columns = self.get_list_attributes()
        id_row = None
        id_data = None
        
        rows_name = []
        rows_data = []
        
        for row in table_columns:
            if row.primary_key:
                id_row = row.row_name
                id_data = row.data
            
            # Обработка специальных типов данных
            data = self._prepare_data_for_save(row)
            rows_data.append(data)
            rows_name.append(row.row_name)
        
        if id_data is None:
            # INSERT
            return await self._insert_data(rows_name, rows_data)
        else:
            # UPDATE
            return await self._update_data(rows_name, rows_data, id_row, id_data)
    
    def _prepare_data_for_save(self, row: ColumnModel) -> Any:
        """Подготавливает данные для сохранения"""
        data = row.data
        
        # Обработка BLOB/JSON данных
        if row.data_type in ('BLOB', 'JSON', 'JSONB') and data is not None:
            try:
                if isinstance(data, (dict, list)):
                    data = json.dumps(data)
            except (TypeError, ValueError):
                pass
        
        return data
    
    @abstractmethod
    async def _insert_data(self, rows_name: List[str], rows_data: List[Any]) -> Any:
        """Абстрактный метод для вставки данных"""
        pass
    
    @abstractmethod
    async def _update_data(self, rows_name: List[str], rows_data: List[Any], 
                          id_row: str, id_data: Any) -> Any:
        """Абстрактный метод для обновления данных"""
        pass
    
    async def load_one(self, id: Any) -> None:
        """Загружает данные из базы данных по ID"""
        # Этот метод будет переопределен в дочерних классах
        pass
    
    async def load_one_custom(self, **kwargs) -> None:
        """Загружает данные из базы данных по произвольным условиям"""
        # Этот метод будет переопределен в дочерних классах
        pass
    
    async def delete(self) -> None:
        """Удаляет текущий экземпляр из базы данных"""
        # Этот метод будет переопределен в дочерних классах
        pass
    
    @classmethod
    async def get_all(cls, db_config: Union[str, Dict[str, Any]], 
                     table: str) -> List['BaseModel']:
        """Возвращает все записи из таблицы"""
        # Этот метод будет переопределен в дочерних классах
        pass
    
    @classmethod
    async def get_all_by(cls, db_config: Union[str, Dict[str, Any]], 
                        table: str, **kwargs) -> List['BaseModel']:
        """Возвращает записи по условиям"""
        # Этот метод будет переопределен в дочерних классах
        pass
    
    @classmethod
    async def execute_query(cls, db_config: Union[str, Dict[str, Any]], 
                          table: str, query: str) -> List['BaseModel']:
        """Выполняет произвольный SQL запрос"""
        # Этот метод будет переопределен в дочерних классах
        pass 