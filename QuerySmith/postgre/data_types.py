class DataTypeDB:
    """
    Содержит типы данных для PostgreSQL
    """

    text = 'TEXT'
    char = 'CHAR({})'
    varchar = 'VARCHAR({})'

    smalint = 'SMALINT'
    integet = 'INTEGET'
    bigint = 'BIGINT'
    decimal = 'DECIMAL'
    real = 'REAL'
    serial = 'SERIAL'

    timestamp = 'TIMESTAMP'
    date = 'DATE'
    time = 'TIME'
    interval = 'INTERVAL'

    boolean = 'BOOLEAN'

    bytea = 'BYTEA'

    json = 'JSON'
    jsonb = 'JSONB'
