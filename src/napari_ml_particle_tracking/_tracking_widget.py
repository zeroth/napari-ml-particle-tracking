import os
import sys
from pathlib import Path
import typing
import copy

import numpy as np
import napari

from qtpy.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox
from superqt import QLabeledSlider as QSlider
from qtpy.QtGui import QStandardItemModel
from qtpy.QtCore import Signal, QItemSelectionModel, QModelIndex, Qt
from ._base_widget import NapariLayersWidget
from ._intensity_plot import IntensityPlotWidget, colors
import pandas as pd

TIME_POINT_SL_MIN = 1

class TrackTableFilterWidget(QWidget):
    track_clicked = Signal(int)
    track_filtered = Signal(list)
    def __init__(self, tracks=[], parent: QWidget = None) -> None:
        super().__init__(parent)
        

        self.sl_time_point = QSlider(Qt.Orientation.Horizontal)
        self.sl_time_point.setTracking(False)
        self.sl_time_point.setMinimum(TIME_POINT_SL_MIN)
        # self.sl_time_point.setMaximum(len(self.display_tracks[-1]))
        # self.sl_time_point.setTickPosition(QSlider.TickPosition.TicksBothSides)
        # self.sl_time_point.setTickInterval(1)
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
        self.sl_time_point.setValue(TIME_POINT_SL_MIN)
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
        self.single_display_track = []
        self.single_display_track_layer = None
        self.tracked_df = pd.DataFrame()
        self.selected_track_layer = None
        self.selected_track_id = None

        self.sb_search_range = QDoubleSpinBox()
        self.sb_search_range.setMinimum(1.0)
        self.sb_search_range.setValue(2.0)
        self.sb_memory = QSpinBox()
        self.sb_memory.setMinimum(0)
        self.sb_memory.setValue(1)

        self.btn_track = QPushButton("Track")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_track)

        self.layer_layout.addRow("Search Range", self.sb_search_range)
        self.layer_layout.addRow("Memory", self.sb_memory)
        self.layout().addLayout(btn_layout)
        self.table = None
        self.table_model = None
        self.sl_min_time = None

        self.table_widget = TrackTableFilterWidget(self.display_tracks)
        self.layout().addWidget(self.table_widget)
        self.table_widget.track_clicked.connect(self._track_selected)
        self.table_widget.track_filtered.connect(self._track_filtered)

        self.plot_widget = IntensityPlotWidget(self.viewer)
        self.layout().addWidget(self.plot_widget)

        self.btn_plot_all = QPushButton("Plot All Inteisity")
        self.btn_fit_all = QPushButton("Fit All Step")
        self.btn_fit_selected = QPushButton("Fit Selected Step")
        btn_intensity_layout = QHBoxLayout()
        btn_intensity_layout.addWidget(self.btn_plot_all)
        btn_intensity_layout.addWidget(self.btn_fit_all)
        btn_intensity_layout.addWidget(self.btn_fit_selected)
        self.layout().addLayout(btn_intensity_layout)

        # init btns
        self.btn_track.clicked.connect(self.track)
        self.comboBoxUpdated.connect(self.update_btns)

        self.save_action.setVisible(True)
        self.open_action.setVisible(True)
        self.saveClicked.connect(self.save)
        self.openClicked.connect(self.open)
        
        self.btn_plot_all.clicked.connect(self.plot_all)
        self.btn_fit_all.clicked.connect(self.fit_all)
        self.btn_fit_selected.clicked.connect(self.fit_selected)
        
        self.update_btns()

    def update_btns(self):
        if self.combo_image_layers.count() and self.combo_mask_layers.count():
            self.btn_track.setDisabled(False)
        else:
            self.btn_track.setDisabled(True)
    
    def track(self):
        from particle_tracking.utils import get_statck_properties, get_tracks

        image_layer_index = self.combo_image_layers.currentData()
        image_layer = self.viewer.layers[image_layer_index].data

        mask_layer_index = self.combo_mask_layers.currentData()
        mask_layer = self.viewer.layers[mask_layer_index].data

        main_pd_frame = get_statck_properties(masks=mask_layer, images=image_layer, show_progress=False)
        search_range = self.sb_search_range.value()
        memory = self.sb_memory.value()
        tracked = get_tracks(main_pd_frame, search_range=search_range, memory=memory)
        self.tracked_df = tracked
        self.pd_to_tracks()

    
    def add_table(self):
        self.display_tracks = copy.deepcopy(self.tracks)
        self.table_widget.set_all_tracks(self.tracks)
        self.display()

    def pd_to_tracks(self):
        from particle_tracking.utils import Track, Point
        tracked = self.tracked_df 
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

    def get_track_by_id(self, id):
        for track in self.tracks:
            if track.id == id:
                return track
        return None

    def show_tracks_layer(self, state):
        if self.selected_track_layer != None:
            self.selected_track_layer.visible = state
    
    def _track_filtered(self, tracks):
        self.display_tracks = tracks
        self.display()

    def display(self):
        
        d_tracks = []

        # prepate tracks to display 
        for t in self.display_tracks:
            d_tracks += t.to_list()
        if self.selected_track_layer != None:
            self.selected_track_layer.data = d_tracks
        else:
            self.selected_track_layer = self.viewer.add_tracks(d_tracks, name="Tracks")
        
        self.show_mask(False)
    
    def _track_selected(self, track_id):
        track = self.get_track_by_id(track_id)
        self.selected_track_id = track_id
        if self.single_display_track_layer == None:
            self.single_display_track_layer = self.viewer.add_tracks(track.to_list(), name=f"Selected Track {track_id}")
        else:
            self.single_display_track_layer.data = track.to_list()
            self.single_display_track_layer.name = f"Selected Track {track_id}"
        
        self.show_tracks_layer(False)

        if track != None:
            self.plot_widget.clear()
            self.plot_widget.draw(track.to_list_by_key('intensity_mean'), "Intensity")

    

    def plot_all(self):
        # plot all intensity
        d_tracks = []
        for t in self.display_tracks:
            d_tracks += [t.to_list_by_key('intensity_mean')]
        self.plot_widget.clear()
        # np_d_track = np.array(d_tracks)
        # print(np_d_track.shape)
        self.plot_widget.draw(d_tracks, "Intensity", multile=True)

    def fit_all(self):
        # plot all intensity
        d_tracks = []
        for t in self.display_tracks:
            d_tracks += [self.detect_steps(t.to_list_by_key('intensity_mean'))[0]]
        self.plot_widget.clear()
        # np_d_track = np.array(d_tracks)
        # print(np_d_track.shape)
        self.plot_widget.draw(d_tracks, "Steps", color=colors['COLOR_2'], multile=True)

    def fit_selected(self):
        track = self.get_track_by_id(self.selected_track_id)
        fit_steps, step_count = self.detect_steps(track.to_list_by_key('intensity_mean'))
        self.plot_widget.draw(fit_steps, f"Total Steps = {step_count}", color=colors['COLOR_2'])

    def detect_steps(self, intensity):
        # Auto step finder
        import particle_tracking.stepfindCore as core
        import particle_tracking.stepfindInOut as sio
        import particle_tracking.stepfindTools as st
        if not len(intensity):
            return
        dataX = np.array(intensity)
        FitX = 0 * dataX

        # multipass:
        for ii in range(0, 3, 1):
            # work remaining part of data:
            residuX = dataX - FitX
            newFitX, _, _, S_curve, best_shot = core.stepfindcore(
                residuX, 0.1
            )
            FitX = st.AppendFitX(newFitX, FitX, dataX)
            # storage for plotting:
            if ii == 0:
                Fits = np.copy(FitX)
                S_curves = np.copy(S_curve)
                best_shots = [best_shot]
            elif best_shot > 0:
                Fits = np.vstack([Fits, FitX])
                S_curves = np.vstack([S_curves, S_curve])
                best_shots = np.hstack([best_shots, best_shot])

        # steps from final fit:
        steptable = st.Fit2Steps(dataX, FitX)
        # self.intensity_plot.set_steps(list(FitX))
        # self.plot_widget.clear()
        return FitX, len(steptable)

    def save(self):
        if not self.tracked_df.empty:
            file_path = QFileDialog.getSaveFileName(self, caption="Save Tracks", directory=str(Path.home()), filter="*.csv")
            self.tracked_df.to_csv(file_path[0], sep=",")
        else:
            QMessageBox.warning(self, "Track Save error", "There are no tracks ")

    def open(self):
        file_path = QFileDialog.getOpenFileName(self, caption="Open Tracks", directory=str(Path.home()), filter="*.csv")
        self.tracked_df = pd.read_csv(file_path[0], sep=',')
        if not self.tracked_df.empty:
            self.pd_to_tracks()
        else:
            QMessageBox.warning(self, "Track Open error", "Csv file is not compatible ")

    