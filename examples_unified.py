"""
Примеры использования QuerySmith с устраненным дублированием кода

Этот файл демонстрирует использование новой архитектуры QuerySmith
с общим базовым классом для PostgreSQL и SQLite.
"""

import asyncio
from QuerySmith import (
    AsyncPGBaseClass, AsyncSQLiteClass, AsyncMySQLClassMySQL,
    ColumnModel, DataType
)
from QuerySmith.query_cache import cache

# PostgreSQL модель
class UserPG(AsyncPGBaseClass):
    def _setup_columns(self):
        self.id = ColumnModel(data=None, row_name="id", data_type=DataType.INTEGER.get_sql_type("postgresql"), primary_key=True)
        self.name = ColumnModel(data=None, row_name="name", data_type=DataType.VARCHAR.get_sql_type("postgresql", 100))
        self.email = ColumnModel(data=None, row_name="email", data_type=DataType.VARCHAR.get_sql_type("postgresql", 255), unique=True)
        self.age = ColumnModel(data=None, row_name="age", data_type=DataType.INTEGER.get_sql_type("postgresql"))
        self.is_active = ColumnModel(data=None, row_name="is_active", data_type=DataType.BOOLEAN.get_sql_type("postgresql"))
    def get_attributes(self):
        return ["id", "name", "email", "age", "is_active"]

# SQLite модель
class ProductSQLite(AsyncSQLiteClass):
    def _setup_columns(self):
        self.id = ColumnModel(data=None, row_name="id", data_type=DataType.INTEGER.get_sql_type("sqlite"), primary_key=True)
        self.name = ColumnModel(data=None, row_name="name", data_type=DataType.TEXT.get_sql_type("sqlite"))
        self.price = ColumnModel(data=None, row_name="price", data_type=DataType.REAL.get_sql_type("sqlite"))
        self.in_stock = ColumnModel(data=None, row_name="in_stock", data_type=DataType.BOOLEAN.get_sql_type("sqlite"))
    def get_attributes(self):
        return ["id", "name", "price", "in_stock"]

# MySQL модель
class UserMySQL(AsyncMySQLClassMySQL):
    def _setup_columns(self):
        self.id = ColumnModel(data=None, row_name="id", data_type=DataType.INTEGER.get_sql_type("mysql"), primary_key=True)
        self.name = ColumnModel(data=None, row_name="name", data_type=DataType.VARCHAR.get_sql_type("mysql", 100))
        self.email = ColumnModel(data=None, row_name="email", data_type=DataType.VARCHAR.get_sql_type("mysql", 255), unique=True)
        self.is_active = ColumnModel(data=None, row_name="is_active", data_type=DataType.BOOLEAN.get_sql_type("mysql"))
    def get_attributes(self):
        return ["id", "name", "email", "is_active"]

async def postgresql_example():
    print("\n=== PostgreSQL Example ===")
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "password",
        "database": "test_db"
    }
    user = UserPG(db_config, "users")
    user.name.data = "Alice"
    user.email.data = "alice@example.com"
    user.age.data = 25
    user.is_active.data = True
    user_id = await user.save()
    print(f"Создан пользователь с ID: {user_id}")
    await user.load_one_custom(name="Alice", email="alice@example.com")
    print(f"Загружен: {user.name.data}, {user.email.data}, {user.age.data}, {user.is_active.data}")
    users = await UserPG.get_all_by(db_config, "users", is_active=True)
    print(f"Активных пользователей: {len(users)}")

async def sqlite_example():
    print("\n=== SQLite Example ===")
    db_path = "sqlite_example.db"
    product = ProductSQLite(db_path, "products")
    product.name.data = "Laptop"
    product.price.data = 999.99
    product.in_stock.data = True
    await product.save()
    await product.load_one_custom(name="Laptop", price=999.99)
    print(f"Загружен продукт: {product.name.data}, {product.price.data}, {product.in_stock.data}")
    products = await ProductSQLite.get_all_by(db_path, "products", name="Laptop", in_stock=True)
    print(f"В наличии ноутбуков: {len(products)}")

async def mysql_example():
    print("\n=== MySQL Example ===")
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "password",
        "db": "test_db"
    }
    user = UserMySQL(db_config, "users")
    user.name.data = "Bob"
    user.email.data = "bob@example.com"
    user.is_active.data = True
    user_id = await user.save()
    print(f"Создан пользователь MySQL с ID: {user_id}")
    await user.load_one_custom(name="Bob", email="bob@example.com")
    print(f"Загружен: {user.name.data}, {user.email.data}, {user.is_active.data}")
    users = await UserMySQL.get_all_by(db_config, "users", is_active=True)
    print(f"Активных пользователей (MySQL): {len(users)}")

async def cache_example_postgresql():
    print("\n=== PostgreSQL Cache Example ===")
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "password",
        "database": "test_db"
    }
    query = "SELECT * FROM users WHERE is_active = true"
    # Первый вызов — обращение к БД
    users1 = await AsyncPGBaseClass.execute_query(db_config, "users", query)
    # Второй вызов — результат из кэша
    users2 = await AsyncPGBaseClass.execute_query(db_config, "users", query)
    print(f"Кэш работает: {users1 is users2 or users1 == users2}")
    cache.clear()
    users3 = await AsyncPGBaseClass.execute_query(db_config, "users", query)
    print(f"После очистки кэша: {users1 is not users3}")

async def cache_example_sqlite():
    print("\n=== SQLite Cache Example ===")
    db_path = "sqlite_example.db"
    query = "SELECT * FROM products WHERE in_stock = 1"
    # Первый вызов — обращение к БД
    products1 = await AsyncSQLiteClass.execute_query(db_path, "products", query)
    # Второй вызов — результат из кэша
    products2 = await AsyncSQLiteClass.execute_query(db_path, "products", query)
    print(f"Кэш работает: {products1 is products2 or products1 == products2}")
    cache.clear()
    products3 = await AsyncSQLiteClass.execute_query(db_path, "products", query)
    print(f"После очистки кэша: {products1 is not products3}")

async def cache_example_mysql():
    print("\n=== MySQL Cache Example ===")
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "password",
        "db": "test_db"
    }
    query = "SELECT * FROM users WHERE is_active = true"
    users1 = await AsyncMySQLClassMySQL.execute_query(db_config, "users", query)
    users2 = await AsyncMySQLClassMySQL.execute_query(db_config, "users", query)
    print(f"Кэш работает: {users1 is users2 or users1 == users2}")
    cache.clear()
    users3 = await AsyncMySQLClassMySQL.execute_query(db_config, "users", query)
    print(f"После очистки кэша: {users1 is not users3}")

async def main():
    print("QuerySmith Examples (Unified)")
    print("=" * 40)
    await postgresql_example()
    await sqlite_example()
    await mysql_example()
    await cache_example_postgresql()
    await cache_example_sqlite()
    await cache_example_mysql()
    print("\nВсе примеры завершены!")

if __name__ == "__main__":
    asyncio.run(main()) 