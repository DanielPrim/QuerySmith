from typing import Any, Optional
from QuerySmith.data_types import DataType

class ColumnModelMySQL:
    """Модель столбца для MySQL"""
    def __init__(self, data: Any, row_name: str, data_type: DataType, len_data_type: Optional[int] = None, primary_key: bool = False, references_table: 'AsyncMySQLClass' = None, unique: bool = False):
        if not hasattr(DataType, data_type.name):
            raise ValueError(f"{data_type} must be an attribute of the class DataType")
        if data_type in (DataType.CHAR, DataType.VARCHAR) and len_data_type is None:
            raise ValueError(f"len_data_type must be set for the type {data_type}")
        if len_data_type:
            data_type_str = data_type.get_sql_type("mysql", len_data_type)
        else:
            data_type_str = data_type.get_sql_type("mysql")
        self.data = data
        self.row_name = row_name
        self.data_type = data_type_str
        self.primary_key = primary_key
        self.references_table = references_table
        self.unique = unique 