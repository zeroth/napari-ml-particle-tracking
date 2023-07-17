from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
from napari_matplotlib.base import BaseNapariMPLWidget
import napari
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton
from typing import List, Optional, Tuple
import matplotlib
import matplotlib.style as mplstyle
import numpy as np
from ._base_widget import NapariLayersWidget,BaseWidget
# Auto step finder
import particle_tracking.stepfindCore as core
import particle_tracking.stepfindInOut as sio
import particle_tracking.stepfindTools as st

# https://davidmathlogic.com/colorblind #  IBM Design Library
COLOR_1 = "#DC267F"
COLOR_2 = "#648FFF"
COLOR_3 = "#785EF0"
COLOR_4 = "#FE6100"
COLOR_5 = "#FFB000"

class IntensityPlotWidget(BaseNapariMPLWidget):
    
    def __init__(
        self,
        napari_viewer: napari.viewer.Viewer,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(napari_viewer=napari_viewer, parent=parent)

        # self._setup_callbacks()
        self.add_single_axes()
        self.data = []
        self.label = None
        self.color = None

    def _on_napari_theme_changed(self) -> None:
        """Update MPL toolbar and axis styling when `napari.Viewer.theme` is changed.

        Note:
            At the moment we only handle the default 'light' and 'dark' napari themes.
        """
        super()._on_napari_theme_changed()
        self.clear()
        self.draw(self.data, self.label, self.color)

    def clear(self) -> None:
        """
        Clear any previously drawn figures.

        This is a no-op, and is intended for derived classes to override.
        """
        with mplstyle.context(self.mpl_style_sheet_path):
            self.axes.clear()

    def draw(self, data, label, color=COLOR_1, multile=False) -> None:
        from matplotlib.legend_handler import HandlerTuple
        if len(data):
            self.data = data
            self.label = label
            self.color = color
            if multile:
                
                lines = []
                for l in range(len(data)):
                    x = np.arange(len(data[l]))
                    self.axes.plot(x, data[l],  label=label)
                    # lines.append(_line)
                    
                # self.axes.legend(handles=[lines])
            else:   
                x = np.arange(len(self.data))
                self.axes.plot(x, self.data, label =label, color=color)
                self.axes.legend()

        # needed
        self.canvas.draw()


class StepFinderWidget(BaseWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer, parent:QWidget=None) -> None:
        super().__init__(parent)
        # self.setLayout(QVBoxLayout())
        self.btn_step_find = QPushButton("Find Steps")
        self.btn_step_find.clicked.connect(self.detect_steps)
        self.intensity_plot = IntensityPlotWidget(napari_viewer)
        self.layout().addWidget(self.intensity_plot)
        self.layout().addWidget(self.btn_step_find)
        self.intensity = []

    def set_track(self, track):
        from particle_tracking.utils import Track
        self.track = track
        self.set_intensity(track.to_list_by_key('intensity_mean'))

        
    def set_intensity(self, intensity):
        self.intensity = intensity
        self.intensity_plot.set_intensity(self.intensity)
    
    def detect_steps(self):
        if not len(self.intensity):
            return
        dataX = np.array(self.intensity)
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
        # steptable = st.Fit2Steps(dataX, FitX)
        self.intensity_plot.set_steps(list(FitX))