"""
Тесты для QuerySmith

Базовые тесты для проверки функциональности библиотеки.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from QuerySmith.postgre import AsyncPGBaseClass, ColumnModelPG, DataTypePG
from QuerySmith.sqlite import AsyncSQLiteClass, ColumnModel, DataTypeDB


class TestDataTypes(unittest.TestCase):
    """Тесты для типов данных"""
    
    def test_postgresql_data_types(self):
        """Тест типов данных PostgreSQL"""
        self.assertEqual(DataTypePG.TEXT, 'TEXT')
        self.assertEqual(DataTypePG.INTEGER, 'INTEGER')
        self.assertEqual(DataTypePG.VARCHAR, 'VARCHAR({})')
        self.assertEqual(DataTypePG.BOOLEAN, 'BOOLEAN')
    
    def test_sqlite_data_types(self):
        """Тест типов данных SQLite"""
        self.assertEqual(DataTypeDB.TEXT, 'TEXT')
        self.assertEqual(DataTypeDB.INTEGER, 'INTEGER')
        self.assertEqual(DataTypeDB.REAL, 'REAL')
        self.assertEqual(DataTypeDB.BOOLEAN, 'BOOLEAN')


class TestColumnModel(unittest.TestCase):
    """Тесты для модели столбца"""
    
    def test_column_model_pg_creation(self):
        """Тест создания модели столбца PostgreSQL"""
        column = ColumnModelPG(
            data="test",
            row_name="test_column",
            data_type=DataTypePG.TEXT,
            primary_key=True
        )
        
        self.assertEqual(column.data, "test")
        self.assertEqual(column.row_name, "test_column")
        self.assertEqual(column.data_type, "TEXT")
        self.assertTrue(column.primary_key)
    
    def test_column_model_sqlite_creation(self):
        """Тест создания модели столбца SQLite"""
        column = ColumnModel(
            data=123,
            row_name="test_column",
            data_type=DataTypeDB.INTEGER,
            unique=True
        )
        
        self.assertEqual(column.data, 123)
        self.assertEqual(column.row_name, "test_column")
        self.assertEqual(column.data_type, "INTEGER")
        self.assertTrue(column.unique)
    
    def test_column_model_invalid_type(self):
        """Тест ошибки при неверном типе данных"""
        with self.assertRaises(ValueError):
            ColumnModelPG(
                data="test",
                row_name="test_column",
                data_type="INVALID_TYPE"
            )
    
    def test_column_model_varchar_without_length(self):
        """Тест ошибки при VARCHAR без указания длины"""
        with self.assertRaises(ValueError):
            ColumnModelPG(
                data="test",
                row_name="test_column",
                data_type=DataTypePG.VARCHAR
            )


class TestBaseModel(unittest.TestCase):
    """Тесты для базовых моделей"""
    
    def test_get_attributes_abstract(self):
        """Тест что абстрактный метод требует реализации"""
        class TestModel(AsyncPGBaseClass):
            def __init__(self):
                super().__init__({}, "test_table")
        
        with self.assertRaises(TypeError):
            TestModel()
    
    def test_get_schema_on_create(self):
        """Тест генерации SQL схемы"""
        class TestModel(AsyncPGBaseClass):
            def __init__(self):
                super().__init__({}, "test_table")
                self.id = ColumnModelPG(
                    data=None,
                    row_name="id",
                    data_type=DataTypePG.INTEGER,
                    primary_key=True
                )
                self.name = ColumnModelPG(
                    data=None,
                    row_name="name",
                    data_type=DataTypePG.VARCHAR,
                    len_data_type=100
                )
            
            def get_attributes(self):
                return ["id", "name"]
        
        model = TestModel()
        schema = model.get_schema_on_create()
        
        self.assertIn("CREATE TABLE test_table", schema)
        self.assertIn("id INTEGER PRIMARY KEY", schema)
        self.assertIn("name VARCHAR(100)", schema)


class TestSQLiteIntegration(unittest.TestCase):
    """Интеграционные тесты для SQLite"""
    
    def setUp(self):
        """Настройка тестов"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        class TestModel(AsyncSQLiteClass):
            def __init__(self, db_path):
                super().__init__(db_path, "test_table")
                self.id = ColumnModel(
                    data=None,
                    row_name="id",
                    data_type=DataTypeDB.INTEGER,
                    primary_key=True
                )
                self.name = ColumnModel(
                    data=None,
                    row_name="name",
                    data_type=DataTypeDB.TEXT
                )
                self.value = ColumnModel(
                    data=None,
                    row_name="value",
                    data_type=DataTypeDB.REAL
                )
            
            def get_attributes(self):
                return ["id", "name", "value"]
        
        self.TestModel = TestModel
    
    def tearDown(self):
        """Очистка после тестов"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    async def test_sqlite_save_and_load(self):
        """Тест сохранения и загрузки данных в SQLite"""
        model = self.TestModel(self.db_path)
        model.name.data = "Test Name"
        model.value.data = 42.5
        
        # Сохранение
        result = await model.save()
        self.assertIsNotNone(result)
        
        # Создание нового экземпляра для загрузки
        loaded_model = self.TestModel(self.db_path)
        await loaded_model.load_one(result)
        
        self.assertEqual(loaded_model.name.data, "Test Name")
        self.assertEqual(loaded_model.value.data, 42.5)
    
    async def test_sqlite_get_all(self):
        """Тест получения всех записей"""
        # Создание нескольких записей
        for i in range(3):
            model = self.TestModel(self.db_path)
            model.name.data = f"Test {i}"
            model.value.data = float(i)
            await model.save()
        
        # Получение всех записей
        all_models = await self.TestModel.get_all(self.db_path, "test_table")
        self.assertEqual(len(all_models), 3)
        
        # Проверка данных
        names = [model.name.data for model in all_models]
        self.assertIn("Test 0", names)
        self.assertIn("Test 1", names)
        self.assertIn("Test 2", names)


class TestPostgreSQLIntegration(unittest.TestCase):
    """Интеграционные тесты для PostgreSQL"""
    
    def setUp(self):
        """Настройка тестов"""
        class TestModel(AsyncPGBaseClass):
            def __init__(self, db_config):
                super().__init__(db_config, "test_table")
                self.id = ColumnModelPG(
                    data=None,
                    row_name="id",
                    data_type=DataTypePG.INTEGER,
                    primary_key=True
                )
                self.name = ColumnModelPG(
                    data=None,
                    row_name="name",
                    data_type=DataTypePG.VARCHAR,
                    len_data_type=100
                )
                self.is_active = ColumnModelPG(
                    data=None,
                    row_name="is_active",
                    data_type=DataTypePG.BOOLEAN
                )
            
            def get_attributes(self):
                return ["id", "name", "is_active"]
        
        self.TestModel = TestModel
        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "user": "test_user",
            "password": "test_password",
            "database": "test_db"
        }
    
    @patch('asyncpg.connect')
    async def test_postgresql_connection(self, mock_connect):
        """Тест подключения к PostgreSQL"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        model = self.TestModel(self.db_config)
        await model.connect()
        
        mock_connect.assert_called_once()
    
    @patch('asyncpg.connect')
    async def test_postgresql_save(self, mock_connect):
        """Тест сохранения в PostgreSQL"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1}
        
        model = self.TestModel(self.db_config)
        model.name.data = "Test Name"
        model.is_active.data = True
        
        result = await model.save()
        self.assertIsNotNone(result)


class TestTransactions(unittest.IsolatedAsyncioTestCase):
    async def test_sqlite_transaction_commit_and_rollback(self):
        import tempfile, os
        db_path = tempfile.mktemp()
        class Model(AsyncSQLiteClass):
            def _setup_columns(self):
                self.id = ColumnModel(data=None, row_name="id", data_type="INTEGER", primary_key=True)
                self.value = ColumnModel(data=None, row_name="value", data_type="TEXT")
            def get_attributes(self):
                return ["id", "value"]
        model = Model(db_path, "t")
        # Коммит
        async with model.transaction():
            model.value.data = "commit"
            await model.save()
        loaded = Model(db_path, "t")
        await loaded.load_one_custom(value="commit")
        self.assertEqual(loaded.value.data, "commit")
        # Роллбек
        try:
            async with model.transaction():
                model.value.data = "rollback"
                await model.save()
                raise Exception("force rollback")
        except Exception:
            pass
        loaded2 = Model(db_path, "t")
        with self.assertRaises(Exception):
            await loaded2.load_one_custom(value="rollback")

    async def test_postgresql_transaction_commit_and_rollback(self):
        # Этот тест требует реальной PostgreSQL и настроенного db_config
        # Пример:
        # db_config = {"host": ..., "port": ..., ...}
        pass

    async def test_mysql_transaction_commit_and_rollback(self):
        # Этот тест требует реальной MySQL и настроенного db_config
        # Пример:
        # db_config = {"host": ..., "port": ..., ...}
        pass


class TestQueryCache(unittest.IsolatedAsyncioTestCase):
    async def test_cache_query_select(self):
        from QuerySmith.query_cache import cache, cache_query
        class Dummy:
            calls = 0
            @cache_query(ttl=2)
            async def select(self, query, *args):
                Dummy.calls += 1
                return f"result-{args}"
        d = Dummy()
        r1 = await d.select("SELECT * FROM t", 1)
        r2 = await d.select("SELECT * FROM t", 1)
        self.assertEqual(r1, r2)
        self.assertEqual(Dummy.calls, 1)
        cache.clear()
        r3 = await d.select("SELECT * FROM t", 1)
        self.assertEqual(Dummy.calls, 2)
    async def test_cache_ttl(self):
        from QuerySmith.query_cache import cache, cache_query
        import asyncio
        class Dummy:
            calls = 0
            @cache_query(ttl=1)
            async def select(self, query, *args):
                Dummy.calls += 1
                return f"result-{args}"
        d = Dummy()
        await d.select("SELECT * FROM t", 2)
        await asyncio.sleep(1.1)
        await d.select("SELECT * FROM t", 2)
        self.assertEqual(Dummy.calls, 2)


def run_tests():
    """Запуск всех тестов"""
    # Создание тестового набора
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавление тестов
    suite.addTests(loader.loadTestsFromTestCase(TestDataTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnModel))
    suite.addTests(loader.loadTestsFromTestCase(TestBaseModel))
    suite.addTests(loader.loadTestsFromTestCase(TestSQLiteIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPostgreSQLIntegration))
    
    # Запуск тестов
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


async def run_async_tests():
    """Запуск асинхронных тестов"""
    print("Запуск асинхронных тестов...")
    
    # SQLite тесты
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    try:
        class TestModel(AsyncSQLiteClass):
            def __init__(self, db_path):
                super().__init__(db_path, "test_table")
                self.id = ColumnModel(
                    data=None,
                    row_name="id",
                    data_type=DataTypeDB.INTEGER,
                    primary_key=True
                )
                self.name = ColumnModel(
                    data=None,
                    row_name="name",
                    data_type=DataTypeDB.TEXT
                )
            
            def get_attributes(self):
                return ["id", "name"]
        
        # Тест создания таблицы
        model = TestModel(db_path)
        await model.ensure_table_exists()
        
        # Тест сохранения
        model.name.data = "Test"
        result = await model.save()
        print(f"SQLite тест: сохранена запись с ID {result}")
        
        # Тест загрузки
        loaded_model = TestModel(db_path)
        await loaded_model.load_one(result)
        print(f"SQLite тест: загружена запись '{loaded_model.name.data}'")
        
        print("SQLite тесты пройдены успешно!")
        
    except Exception as e:
        print(f"Ошибка в SQLite тестах: {e}")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


if __name__ == "__main__":
    print("QuerySmith Tests")
    print("=" * 50)
    
    # Запуск синхронных тестов
    print("Запуск синхронных тестов...")
    success = run_tests()
    
    if success:
        print("Синхронные тесты пройдены успешно!")
    else:
        print("Некоторые синхронные тесты не прошли!")
    
    # Запуск асинхронных тестов
    asyncio.run(run_async_tests())
    
    print("\nВсе тесты завершены!") 