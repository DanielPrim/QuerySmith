from typing import Any

from QuerySmith.sqlite.data_types import DataTypeDB


class ColumnModel:
    """
    Модель столбца
    """

    from QuerySmith.postgre.base_model import AsyncPGBaseClass

    def __init__(self,  data: Any | None,
                 row_name: str, data_type: DataTypeDB,
                 len_data_type: int = None, primary_key: bool = False,
                 references_table: AsyncPGBaseClass = None, unique: bool = False):
        """
        :param data: Значение хранимое в ячейке таблицы
        :param row_name: Название столбца в таблице
        :param data_type: Тип данных в таблице
        :param len_data_type: (Опционально) Если тип данных подразумевает указание длины, в противном случае None
        :param primary_key: (Опционально) True если является первичным ключом, в противном случае False
        :param references_table: (Опционально) Если ячейка является внешним ключом к другой таблице
        :param unique: (Опционально) Если значение должно быть уникальным
        """
        if not hasattr(DataTypeDB, data_type):
            raise ValueError(f"{data_type} must be an attribute of the class DataTypeDB")

        data_type_str = getattr(DataTypeDB, data_type)

        if '{}' in data_type_str:
            if len_data_type is not None:
                data_type_str = data_type_str.format(len_data_type)
            else:
                raise ValueError(f"len_data_type must be set for the type {data_type_str}")
        self.data = data
        self.row_name = row_name
        self.data_type = data_type_str
        self.primary_key = primary_key
        self.references_table = references_table
        self.unique = unique