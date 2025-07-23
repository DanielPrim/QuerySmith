# QuerySmith

QuerySmith — это Python библиотека для быстрой и удобной работы с SQL базами данных. Поддерживает PostgreSQL, SQLite и MySQL с асинхронным API и единым интерфейсом.

## Особенности

- 🚀 **Асинхронная работа** — полная поддержка async/await
- 🗄️ **Множественные БД** — PostgreSQL, SQLite, MySQL
- 🔧 **Автоматические миграции** — создание и обновление схемы таблиц
- 🛡️ **Типизация** — полная поддержка типов данных
- 🔗 **Связи между таблицами** — поддержка внешних ключей
- 📝 **Автогенерация SQL** — автоматическое создание запросов
- 🔍 **Гибкие выборки** — поддержка поиска по нескольким условиям через kwargs (для всех поддерживаемых СУБД)

## Установка

```bash
pip install query-smith
```

Или установка из исходного кода:

```bash
git clone https://github.com/DanielPrim/QuerySmith.git
cd QuerySmith
pip install -e .
```

## Быстрый старт

### PostgreSQL

```python
import asyncio
from QuerySmith import AsyncPGBaseClass, ColumnModel, DataType

class User(AsyncPGBaseClass):
    def _setup_columns(self):
        self.id = ColumnModel(data=None, row_name="id", data_type=DataType.INTEGER.get_sql_type("postgresql"), primary_key=True)
        self.name = ColumnModel(data=None, row_name="name", data_type=DataType.VARCHAR.get_sql_type("postgresql", 100))
        self.email = ColumnModel(data=None, row_name="email", data_type=DataType.VARCHAR.get_sql_type("postgresql", 255), unique=True)
        self.is_active = ColumnModel(data=None, row_name="is_active", data_type=DataType.BOOLEAN.get_sql_type("postgresql"))
    def get_attributes(self):
        return ["id", "name", "email", "is_active"]

async def main():
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "password",
        "database": "test_db"
    }
    user = User(db_config, "users")
    user.name.data = "Alice"
    user.email.data = "alice@example.com"
    user.is_active.data = True
    await user.save()
    await user.load_one_custom(name="Alice", email="alice@example.com")
    print(user.name.data, user.email.data, user.is_active.data)

asyncio.run(main())
```

### SQLite

```python
import asyncio
from QuerySmith import AsyncSQLiteClass, ColumnModel, DataType

class Product(AsyncSQLiteClass):
    def _setup_columns(self):
        self.id = ColumnModel(data=None, row_name="id", data_type=DataType.INTEGER.get_sql_type("sqlite"), primary_key=True)
        self.name = ColumnModel(data=None, row_name="name", data_type=DataType.TEXT.get_sql_type("sqlite"))
        self.price = ColumnModel(data=None, row_name="price", data_type=DataType.REAL.get_sql_type("sqlite"))
        self.in_stock = ColumnModel(data=None, row_name="in_stock", data_type=DataType.BOOLEAN.get_sql_type("sqlite"))
    def get_attributes(self):
        return ["id", "name", "price", "in_stock"]

async def main():
    db_path = "database.db"
    product = Product(db_path, "products")
    product.name.data = "Laptop"
    product.price.data = 999.99
    product.in_stock.data = True
    await product.save()
    await product.load_one_custom(name="Laptop", price=999.99)
    print(product.name.data, product.price.data, product.in_stock.data)
    products = await Product.get_all_by(db_path, "products", name="Laptop", in_stock=True)
    print(f"В наличии ноутбуков: {len(products)}")

asyncio.run(main())
```

### MySQL

```python
import asyncio
from QuerySmith import AsyncMySQLClassMySQL, ColumnModel, DataType

class UserMySQL(AsyncMySQLClassMySQL):
    def _setup_columns(self):
        self.id = ColumnModel(data=None, row_name="id", data_type=DataType.INTEGER.get_sql_type("mysql"), primary_key=True)
        self.name = ColumnModel(data=None, row_name="name", data_type=DataType.VARCHAR.get_sql_type("mysql", 100))
        self.email = ColumnModel(data=None, row_name="email", data_type=DataType.VARCHAR.get_sql_type("mysql", 255), unique=True)
        self.is_active = ColumnModel(data=None, row_name="is_active", data_type=DataType.BOOLEAN.get_sql_type("mysql"))
    def get_attributes(self):
        return ["id", "name", "email", "is_active"]

async def main():
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
    await user.save()
    await user.load_one_custom(name="Bob", email="bob@example.com")
    print(user.name.data, user.email.data, user.is_active.data)
    users = await UserMySQL.get_all_by(db_config, "users", is_active=True)
    print(f"Активных пользователей (MySQL): {len(users)}")

asyncio.run(main())
```

## Гибкие выборки и фильтрация

- **get_all_by**: позволяет искать записи по любому количеству условий (kwargs)
- **load_one_custom**: загружает одну запись по любому количеству условий (kwargs)

```python
# Пример для SQLite
products = await Product.get_all_by(db_path, "products", name="Laptop", price=999.99, in_stock=True)

# Пример для PostgreSQL
users = await User.get_all_by(db_config, "users", name="Alice", email="alice@example.com")

# Пример для MySQL
users = await UserMySQL.get_all_by(db_config, "users", is_active=True)
```

## Транзакции

QuerySmith поддерживает асинхронные транзакции для всех СУБД. Вы можете группировать несколько операций в одну транзакцию, чтобы гарантировать атомарность изменений.

**Пример для PostgreSQL:**
```python
async with user.transaction():
    await user.save()
    await order.save()
```

**Пример для SQLite:**
```python
async with product.transaction():
    await product.save()
    await another_product.save()
```

**Пример для MySQL:**
```python
async with user_mysql.transaction():
    await user_mysql.save()
    await another_user.save()
```

- Все изменения внутри блока будут либо зафиксированы (`commit`), либо полностью отменены (`rollback`) при ошибке.
- Интерфейс одинаков для всех поддерживаемых СУБД.

## Поддерживаемые типы данных

- `TEXT`, `CHAR(n)`, `VARCHAR(n)`
- `SMALLINT`, `INTEGER`, `BIGINT`, `DECIMAL`, `REAL`, `SERIAL`
- `TIMESTAMP`, `DATE`, `TIME`, `INTERVAL`
- `BOOLEAN`
- `BLOB`/`BYTEA`
- `JSON`, `JSONB`

## Основные методы

- `save()` — сохранение объекта в БД
- `load_one(id)` — загрузка по ID
- `load_one_custom(**kwargs)` — загрузка по произвольным условиям
- `delete()` — удаление объекта
- `get_all(db_config, table)` — получение всех записей
- `get_all_by(db_config, table, **kwargs)` — получение по условиям
- `execute_query(db_config, table, query)` — выполнение произвольного запроса
- `get_schema_on_create()` — генерация SQL для создания таблицы
- `create_migration_file(schema)` — создание файла миграции
- `ensure_table_exists()` — проверка и создание таблицы

## Миграции

Библиотека автоматически создает файлы миграций в папках:
- `./migrations_postgre/` — для PostgreSQL
- `./migrations_sqlite/` — для SQLite
- `./migrations_mysql/` — для MySQL

## Кэширование запросов

QuerySmith поддерживает кэширование SELECT-запросов для ускорения работы и снижения нагрузки на базу данных.

- Кэш работает для методов execute_query (и может быть расширен на другие методы).
- Кэш хранится в памяти (in-memory), поддерживает TTL (время жизни кэша).
- При повторном запросе с теми же параметрами результат возвращается мгновенно.
- Кэш автоматически сбрасывается по истечении TTL или вручную.

**Пример:**
```python
from QuerySmith.query_cache import cache

# Очистить кэш вручную
cache.clear()
```

- По умолчанию TTL = 60 секунд. Можно изменить при инициализации QueryCache.
- Кэширование работает только для SELECT-запросов.

**Преимущества:**
- Ускоряет повторные выборки
- Снижает нагрузку на БД
- Повышает отказоустойчивость

## Требования

- Python 3.9+
- asyncpg (для PostgreSQL)
- aiosqlite (для SQLite)
- aiomysql (для MySQL)

## Лицензия

MIT License

## Автор

DanielPrim — [GitHub](https://github.com/DanielPrim)

## Вклад в проект

Приветствуются pull request'ы! Пожалуйста, убедитесь, что:

1. Код соответствует стилю проекта
2. Добавлены тесты для новой функциональности
3. Обновлена документация

## Планы развития

- [ ] Добавление unit-тестов
- [ ] Улучшение документации
- [ ] Создание CLI инструмента для миграций и генерации моделей
- [ ] Поддержка Redis/Memcached кэша
- [ ] Автоматическая инвалидация кэша при изменениях
- [ ] Генерация Swagger/OpenAPI схем для моделей
- [ ] Интеграция с Alembic для сложных миграций
- [ ] Поддержка миграций для MySQL
- [ ] Расширенные типы данных (ENUM, ARRAY, JSONB для SQLite/MySQL)
- [ ] Интеграция с FastAPI/Django
- [ ] Автоматическое тестирование моделей
- [ ] Поддержка миграций через UI
