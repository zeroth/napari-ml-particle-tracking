import os
import sys
from pathlib import Path
import typing
import copy

import numpy as np
import napari

from qtpy.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QListWidget, QListWidgetItem, QSlider, QSpinBox, QDoubleSpinBox
from qtpy.QtGui import QStandardItemModel
from qtpy.QtCore import Signal, QItemSelectionModel, QModelIndex, Qt
from ._base_widget import NapariLayersWidget

class TrackTableFilterWidget(QWidget):
    track_clicked = Signal(int)
    track_filtered = Signal(list)
    def __init__(self, tracks=[], parent: QWidget = None) -> None:
        super().__init__(parent)
        

        self.sl_time_point = QSlider(Qt.Orientation.Horizontal)
        self.sl_time_point.setTracking(False)
        self.sl_time_point.setMinimum(1)
        # self.sl_time_point.setMaximum(len(self.display_tracks[-1]))
        self.sl_time_point.setTickPosition(QSlider.TicksAbove)
        self.sl_time_point.setTickInterval(1)
        self.lw_tracks = QListWidget()

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("Time point filter"))
        self.layout().addWidget(self.sl_time_point)
        self.layout().addWidget(QLabel("Tracks"))
        self.layout().addWidget(self.lw_tracks)
        self.lw_tracks.itemClicked.connect(self._track_clicked)
        self.sl_time_point.valueChanged.connect(self._update_tracks)

        self.all_tracks = tracks
        self.display_tracks = copy.deepcopy(tracks)
        self.populate_tracks()

    def set_all_tracks(self, tracks):
        self.all_tracks = tracks
        self.display_tracks = copy.deepcopy(tracks)
        
        self.populate_tracks()

    def _track_clicked(self,item):
        track_id = item.data(Qt.UserRole+1)
        self.track_clicked.emit(track_id)
    
    def populate_tracks(self):
        if not len(self.display_tracks):
            return
        self.display_tracks.sort(key=len)
        self.lw_tracks.clear()
        self.sl_time_point.setMaximum(len(self.display_tracks[-1]))
        for index, track in enumerate(self.display_tracks):
            list_item = QListWidgetItem()
            list_item.setText(f'{index} : {track.id} - ({len(track)})')
            list_item.setData(Qt.UserRole+1, track.id)
            self.lw_tracks.addItem(list_item)
    
    def _update_tracks(self, val):
        if not  len(self.all_tracks):
            return
        self.display_tracks = list(filter(lambda t: len(t) >= val, self.all_tracks))
        self.populate_tracks()
        self.track_filtered.emit(self.display_tracks)
        


class TrackingWidget(NapariLayersWidget):
    from particle_tracking.utils import Track
    track_selected = Signal(Track)
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__(napari_viewer)
        self.display_tracks = []
        self.current_track_layer = None
        self.sb_search_range = QDoubleSpinBox()
        self.sb_search_range.setMinimum(1.0)
        self.sb_search_range.setValue(2.0)
        self.sb_memory = QSpinBox()
        self.sb_memory.setMinimum(0)
        self.sb_memory.setValue(1)

        self.btn_track = QPushButton("Track")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_track)

        self.layout().addRow("Search Range", self.sb_search_range)
        self.layout().addRow("Memory", self.sb_memory)
        self.layout().addRow(btn_layout)
        self.table = None
        self.table_model = None
        self.sl_min_time = None

        self.table_widget = TrackTableFilterWidget(self.display_tracks)
        self.layout().addRow(self.table_widget)
        self.table_widget.track_clicked.connect(self._track_selected)
        self.table_widget.track_filtered.connect(self._track_filtered)

        # init btns
        self.btn_track.clicked.connect(self.track)
        self.comboBoxUpdated.connect(self.update_btns)
        self.update_btns()

    def update_btns(self):
        if self.combo_image_layers.count() and self.combo_mask_layers.count():
            self.btn_track.setDisabled(False)
        else:
            self.btn_track.setDisabled(True)
    
    def track(self):
        from particle_tracking.utils import get_statck_properties, get_tracks, Track, Point

        image_layer_index = self.combo_image_layers.currentData()
        image_layer = self.viewer.layers[image_layer_index].data

        mask_layer_index = self.combo_mask_layers.currentData()
        mask_layer = self.viewer.layers[mask_layer_index].data

        main_pd_frame = get_statck_properties(masks=mask_layer, images=image_layer, show_progress=False)
        search_range = self.sb_search_range.value()
        memory = self.sb_memory.value()
        tracked = get_tracks(main_pd_frame, search_range=search_range, memory=memory)

        track_ids = tracked['particle'].unique()
        accepted_track_count = 0
        tracks = []
        points = []
        track_objs = []
        for track_id in track_ids:
            if len(list(tracked[tracked['particle'] == track_id]['frame'])) > 1:
                accepted_track_count +=1
                track = Track()
                track.init_by_dataframe(tracked[tracked['particle'] == track_id].copy().reset_index(drop=True), 'particle')
                # for ti, r in track.iterrows():
                track_objs.append(track)
                tracks += track.to_list()
                points += track.to_points_list()
        self.tracks = track_objs
        self.add_table()
    
    def add_table(self):
        self.display_tracks = copy.deepcopy(self.tracks)
        self.table_widget.set_all_tracks(self.tracks)
        self.display()

    def get_track_by_id(self, id):
        for track in self.tracks:
            if track.id == id:
                return track
        return None
    
    def _track_selected(self, track_id):
        track = self.get_track_by_id(track_id)
        if track != None:
            self.track_selected.emit(track)
    
    def _track_filtered(self, tracks):
        self.display_tracks = tracks
        self.display()

    def display(self):
        
        d_tracks = []

        # prepate tracks to display 
        for t in self.display_tracks:
            d_tracks += t.to_list()
        if self.current_track_layer != None:
            self.current_track_layer.data = d_tracks
        else:
            self.current_track_layer = self.viewer.add_tracks(d_tracks, name="Tracks")
        
        self.show_mask(False)
