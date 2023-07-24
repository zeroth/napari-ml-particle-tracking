import os
import sys
from pathlib import Path
from typing import Optional
from PyQt5 import QtCore
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget
import numpy as np
import tifffile
import pandas as pd
from pandas.core.groupby.generic import DataFrameGroupBy

from qtpy.QtWidgets import QWidget, QTableView, QVBoxLayout
from qtpy.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant

class DataFrameModel(QAbstractTableModel):
    def __init__(self, parent: QObject = None, dataframe: pd.DataFrame=pd.DataFrame() ) -> None:
        super().__init__(parent)
        self.dataframe = dataframe
    
    def setDataframe(self, dataframe: pd.DataFrame):
        self.beginResetModel()
        self.dataframe  = dataframe
        self.endResetModel()

    def rowCount(self, parent = QModelIndex())-> int:
        return self.dataframe.shape[0]

    def columnCount(self, parent = QModelIndex()) -> int:
        return self.dataframe.shape[1]

    def data(self, index, role = Qt.DisplayRole)-> QVariant:
        if (not index.isValid()) or (role != Qt.DisplayRole):
            return QVariant()
        if role == Qt.DisplayRole:
            return str(self.dataframe.iat[index.row(), index.column()])

    def headerData(self, section, orientation, role = Qt.DisplayRole) -> QVariant:
        if role == Qt.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.dataframe.columns[section]
            elif orientation == Qt.Orientation.Vertical:
                return str(section)

class DataFrameGroupModel(QAbstractTableModel):
    def __init__(self, parent: QObject = None, dataframe: DataFrameGroupBy=DataFrameGroupBy(pd.DataFrame()), headers =  ['Group Name', 'Length']) -> None:
        super().__init__(parent)
        self.dataframe = dataframe
        self.headers = headers
    
    def setDataframe(self, dataframe: DataFrameGroupBy):
        self.beginResetModel()
        self.dataframe  = dataframe
        self.endResetModel()
    
    def setHeader(self, headers):
        self.beginResetModel()
        self.headers = headers
        self.endResetModel()

    def rowCount(self, parent = QModelIndex())-> int:
        if hasattr(self.dataframe, 'groups'):
            return len(self.dataframe.groups)
        return 0

    def columnCount(self, parent = QModelIndex()) -> int:
        return 2

    def data(self, index, role = Qt.DisplayRole)-> QVariant:
        if (not index.isValid()) or (role != Qt.DisplayRole):
            return QVariant()
        if role == Qt.DisplayRole:
            _group_key = list(self.dataframe.groups.keys())[index.row()]
            _group_len = len(self.dataframe.get_group(_group_key))
            _data = [_group_key, _group_len]
            return str(_data[index.column()])

    def headerData(self, section, orientation, role = Qt.DisplayRole) -> QVariant:
        if role == Qt.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.headers[section]
            elif orientation == Qt.Orientation.Vertical:
                return str(section)


class PandasTable(QWidget):
    def __init__(self, parent: QWidget = None,) -> None:
        super().__init__(parent)

        self.setLayout(QVBoxLayout())
        self.table_view = QTableView()
        self.layout().addWidget(self.table_view)

        self.model = DataFrameGroupModel()
        self.table_view.setModel(self.model)
    
    def setDataframe(self, dataframe):
        self.model.setDataframe(dataframe)

if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    pdf = pd.read_csv("D:/Data/Sudipta/Arpan/test_np/tracks_m2.csv")
    # pdf = pd.DataFrame(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
    #                columns=['a', 'b', 'c'])
    table = PandasTable()
    table.setDataframe(pdf.groupby('particle'))
    table.show()
    app.exec_()