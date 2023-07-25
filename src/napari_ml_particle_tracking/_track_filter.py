import os
import sys
from pathlib import Path
from typing import Optional
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
import numpy as np
import tifffile
from qtpy.QtWidgets import QWidget, QTableView, QVBoxLayout
from qtpy.QtCore import QItemSelectionModel, Qt, QModelIndex
from superqt import QLabeledRangeSlider
from napari_ml_particle_tracking._table_widget import DataFrameModel
import pandas as pd

def create_display_dataframe(dataframe:pd.DataFrame, group_column:str='particle', count_column:str='frame')->pd.DataFrame:
        df_group = dataframe.groupby(group_column, group_keys=True)[count_column].count()
        return pd.DataFrame(df_group)

# TODO: add plots for all tracks histgram and selected track intensity

class TrackFilter(QWidget):
    def __init__(self, parent: QWidget = None ,) -> None:
        super().__init__(parent)
        self.dataframe = pd.DataFrame()
        self.display_dataframe = pd.DataFrame()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.table = QTableView()
        self.data_model = DataFrameModel()
        self.table.setModel(self.data_model)
        self.table_selection = QItemSelectionModel(self.data_model)
        self.table.setSelectionModel(self.table_selection)

        self.sl_length = QLabeledRangeSlider()
        self.sl_length.setOrientation(Qt.Orientation.Horizontal)

        self.layout.addWidget(self.sl_length)
        self.layout.addWidget(self.table)

        self.init()
    
    def init(self):
        self.sl_length.valueChanged.connect(self.length_changed)
        self.table_selection.currentChanged.connect(self.table_current_changed)
    
    def table_current_changed(self, current, previous):
        if (not current.isValid()):
            return
        
        print(f"{current.row()} - {self.data_model.data(current)}")
        
        #  currentChanged(const QModelIndex &current, const QModelIndex &previous)

    def set_dataframe(self, dataframe:pd.DataFrame):
        self.dataframe = dataframe
        self.display_dataframe_all = create_display_dataframe(dataframe=dataframe, group_column='particle', count_column='frame')
        self.display_dataframe = self.display_dataframe_all
        self.data_model.setDataframe(self.display_dataframe)
        data_range = (np.min(self.display_dataframe.values), np.max(self.display_dataframe.values))
        self.sl_length.setRange(data_range[0], data_range[1])
        self.sl_length.setValue(data_range)

    def length_changed(self, vrange):
        vmin, vmax = vrange
        # print("range:", vmin, vmax)
        self.display_dataframe = self.display_dataframe_all[(self.display_dataframe_all['frame'] >= vmin) & (self.display_dataframe_all['frame'] <= vmax)]
        self.data_model.setDataframe(self.display_dataframe)

if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    pdf = pd.read_csv("D:/Data/Sudipta/Arpan/test_np/tracks_m2.csv")
    # pdf = pd.DataFrame(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
    #                columns=['a', 'b', 'c'])
    table = TrackFilter()
    table.set_dataframe(pdf)
    table.show()
    app.exec_()