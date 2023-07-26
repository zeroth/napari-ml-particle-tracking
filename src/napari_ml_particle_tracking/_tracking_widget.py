import os
import sys
from pathlib import Path
import typing
import copy

import numpy as np
import napari
from napari.utils import progress

from qtpy.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox
from superqt import QLabeledSlider as QSlider
from qtpy.QtGui import QStandardItemModel
from qtpy.QtCore import Signal, QItemSelectionModel, QModelIndex, Qt
from ._base_widget import NapariLayersWidget
from ._track_filter import TrackFilter, tracks_frame_count_meta
import pandas as pd


class TrackingWidget(NapariLayersWidget):
    def __init__(self, napari_viewer: napari.viewer.Viewer = None, parent: QWidget = None):
        super().__init__(napari_viewer, parent)

        # members
        self.filtered_track_layer:napari.layers.Tracks = None
        self.tracks = np.zeros([1])
        self.steps_info = pd.DataFrame()
        #/ members


        self.comboBoxUpdated.connect(self.update_btns)
        self.save_action.setVisible(True)
        self.open_action.setVisible(True)
        self.saveClicked.connect(self.save)
        self.openClicked.connect(self.open)

        self.sb_search_range = QDoubleSpinBox()
        self.sb_search_range.setMinimum(1.0)
        self.sb_search_range.setValue(2.0)
        self.sb_memory = QSpinBox()
        self.sb_memory.setMinimum(0)
        self.sb_memory.setValue(1)

        self.btn_track = QPushButton("Track")
        

        self.layer_layout.addRow("Search Range", self.sb_search_range)
        self.layer_layout.addRow("Memory", self.sb_memory)
        self.layout().addWidget(self.btn_track)

        self.track_filter_widget = TrackFilter()
        self.layout().addWidget(self.track_filter_widget)
        # self.track_filter_widget.metaUpdated.connect(self.pd_to_tracks)
        self.btn_display_track = QPushButton("Display Tracks")
        self.btn_analyse_steps = QPushButton("Analyse Steps")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_analyse_steps)
        btn_layout.addWidget(self.btn_display_track)

        self.layout().addLayout(btn_layout)
        self.btn_display_track.clicked.connect(self.pd_to_tracks)
        self.btn_analyse_steps.clicked.connect(self.analyse_steps)
        
    def update_btns(self):
        if self.combo_image_layers.count() and self.combo_mask_layers.count():
            self.btn_track.setDisabled(False)
        else:
            self.btn_track.setDisabled(True)

    def save(self):
        if not self.tracked_df.empty:
            file_path = QFileDialog.getSaveFileName(self, caption="Save Tracks", directory=str(Path.home()), filter="*.csv")
            self.tracked_df.to_csv(file_path[0], sep=",")
        else:
            QMessageBox.warning(self, "Track Save error", "There are no tracks ")

    def open(self):
        file_path = QFileDialog.getOpenFileName(self, caption="Open Tracks", directory=str(Path.home()), filter="*.csv")
        self.tracked_df = pd.read_csv(file_path[0], sep=',')
        self.tracked_df_group = self.tracked_df.groupby('particle', as_index=False, group_keys=True, dropna=True)
        if not self.tracked_df.empty:
            meta_tracks = tracks_frame_count_meta(self.tracked_df, track_id_col='particle', frame_col='frame')
            self.track_filter_widget.set_data(self.tracked_df, meta_tracks)
            # self.pd_to_tracks()
        else:
            QMessageBox.warning(self, "Track Open error", "Csv file is not compatible ")
    
    def pd_to_tracks(self):
        print("pd_to_tracks")
        self.btn_display_track.setDisabled(True)
        track_ids = self.track_filter_widget.get_current_meta()['particle']
        if self.tracks.ndim >1:
            print("track display check ", len(self.tracks), len(track_ids))
            if len(self.tracks) == len(track_ids):
                return

        self.tracks = []
        for id in progress(track_ids, desc="Creating tracks"):
            track:pd.DataFrame = self.tracked_df_group.get_group(id)
            if not len(self.tracks) :
                self.tracks = track[['particle', 'frame', 'y', 'x']].to_numpy()
            else:
                self.tracks = np.concatenate([self.tracks, track[['particle', 'frame', 'y', 'x']].to_numpy()])
        
        
        if self.filtered_track_layer == None:
            self.filtered_track_layer = self.viewer.add_tracks(self.tracks, name="Tracks")
        else:
            self.filtered_track_layer.data = self.tracks
        self.btn_display_track.setDisabled(False)

    def detect_steps(self, intensity):
        # Auto step finder
        import particle_tracking.stepfindCore as core
        import particle_tracking.stepfindInOut as sio
        import particle_tracking.stepfindTools as st
        from particle_tracking.utils import Fit2StepsTable
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
        steptable = Fit2StepsTable(dataX, FitX)

        # self.intensity_plot.set_steps(list(FitX))
        # self.plot_widget.clear()
        return FitX, steptable

    def analyse_steps(self):
        self.btn_analyse_steps.setDisabled(True)
        track_ids = self.track_filter_widget.get_current_meta()['particle']
        for id in progress(track_ids, desc="Detecting steps"):
            track:pd.DataFrame = self.tracked_df_group.get_group(id)
            intensity = track['intensity_mean']
            fitx, steptable = self.detect_steps(intensity)
            print(f"track_id: {id}, step count: {len(steptable)}, inteisitylen : {len(intensity)}")
            self.track_filter_widget.update_meta(id, 'step_count', len(steptable))
            steps_df  = pd.DataFrame(steptable)
            steps_df['particle'] = id
            self.steps_info = pd.concat([self.steps_info, steps_df])

        self.btn_analyse_steps.setDisabled(False)

        
