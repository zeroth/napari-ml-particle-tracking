import os
import sys
from pathlib import Path
from typing import Optional
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
import napari
import numpy as np
import tifffile
import pandas as pd
from napari.utils import progress

from qtpy.QtWidgets import QWidget, QTableView, QVBoxLayout, QHBoxLayout, QTabWidget, QComboBox, QPushButton,\
                            QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox
from qtpy.QtCore import QItemSelectionModel, Qt, QModelIndex, Signal
from superqt import QLabeledRangeSlider

from ._table_widget import DataFrameModel
from ._plots import HistogramWidget
from ._base_widget import NapariLayersWidget

def create_display_dataframe(dataframe:pd.DataFrame, group_column:str='particle', count_column:str='frame')->pd.DataFrame:
        df_group = dataframe.groupby(group_column, group_keys=True)[count_column].count()
        return pd.DataFrame(df_group)

def tracks_frame_count_meta(dataframe:pd.DataFrame, track_id_col:str='particle', frame_col:str= 'frame')-> pd.DataFrame:
    sr = dataframe.groupby(track_id_col, as_index=False, group_keys=True, dropna=True)[frame_col].count()
    return pd.DataFrame(sr)


class PropertiesComboBox(QComboBox):
    def __init__(self, properties:list, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.addItems(properties)

    def set_properties(self, properties):
        self.clear()
        self.addItems(properties)


class TrackFilter(QWidget):
    metaUpdated = Signal()
    def __init__(self, parent: QWidget = None ,) -> None:
        super().__init__(parent)
        self.database = pd.DataFrame()
        self.database_meta = pd.DataFrame()
        self.display_meta = pd.DataFrame()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.tab_widget = QTabWidget()
        ## Histogram
        self.histogram_widget = HistogramWidget()
        self.tab_widget.addTab(self.histogram_widget, "Histogram")
        ## /Histogram
        ## Table
        self.table = QTableView()
        self.data_model = DataFrameModel()
        self.table.setModel(self.data_model)
        self.table_selection = QItemSelectionModel(self.data_model)
        self.table.setSelectionModel(self.table_selection)
        self.tab_widget.addTab(self.table, "Property Table")
        ## /Table

        control_layout = QHBoxLayout()
        self.cb_properties = PropertiesComboBox([])
        self.sl_length = QLabeledRangeSlider()
        self.sl_length.setOrientation(Qt.Orientation.Horizontal)
        control_layout.addWidget(self.sl_length)
        control_layout.addWidget(self.cb_properties)


        self.layout.addLayout(control_layout)
        self.layout.addWidget(self.tab_widget)
    
    def init(self):
        self.sl_length.valueChanged.connect(self.length_changed)
        self.sl_length.sliderReleased.connect(self.range_change)
        self.table_selection.currentChanged.connect(self.table_current_changed)
        self.cb_properties.currentTextChanged.connect(self.update_view)
    
    def range_change(self):
        print("range_change")

    def table_current_changed(self, current, previous):
        if (not current.isValid()):
            return
        
        print(f"{current.row()} - {self.data_model.data(current)}")
        
        #  currentChanged(const QModelIndex &current, const QModelIndex &previous)

    def set_data(self, database:pd.DataFrame, database_meta:pd.DataFrame, default_filter:str='frame'):
        self.database = database
        self.database_meta = database_meta
        self.display_meta = self.database_meta

        self.cb_properties.set_properties(self.database_meta.columns)
        self.cb_properties.setCurrentText(default_filter)
        self.update_view()
        self.init()
        
    def update_view(self):
        current_filter = self.cb_properties.currentText()
        self.data_model.setDataframe(self.display_meta)
        data_range = (np.min(self.display_meta[current_filter]), np.max(self.display_meta[current_filter]))
        self.sl_length.setRange(data_range[0], data_range[1])
        self.sl_length.setValue(data_range)
        self.histogram_widget.draw(self.display_meta[current_filter], label=current_filter)

    def length_changed(self, vrange):
        vmin, vmax = vrange
        # print("range:", vmin, vmax)
        current_filter = self.cb_properties.currentText()
        self.display_meta = self.database_meta[(self.database_meta[current_filter] >= vmin) & (self.database_meta[current_filter] <= vmax)]
        self.data_model.setDataframe(self.display_meta)
        self.histogram_widget.draw(self.display_meta[current_filter], label=current_filter)
        self.metaUpdated.emit()
    
    def get_current_meta(self):
        return self.display_meta
    
    def update_meta(self, track_id, col_nam, val):
        self.database_meta.loc[self.database_meta['particle']==track_id, col_nam] = val
        current_range = (self.sl_length.minimum(), self.sl_length.maximum())
        self.length_changed(current_range)
        current_filter = self.cb_properties.currentText()
        self.cb_properties.set_properties(self.database_meta.columns)
        self.cb_properties.setCurrentText(current_filter)
        # tracks.loc[tracks['particle'] == 64, 'step_size'] = 12


if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    pdf = pd.read_csv("D:/Data/Sudipta/Arpan/test_np/tracks_m2.csv")
    meta_pdf = tracks_frame_count_meta(pdf, track_id_col='particle', frame_col='frame')
    # pdf = pd.DataFrame(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
    #                columns=['a', 'b', 'c'])
    table = TrackFilter()
    table.set_data(pdf, meta_pdf, default_filter='frame')
    table.show()
    app.exec_()