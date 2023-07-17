from typing import TYPE_CHECKING
import numpy as np
from magicgui import magic_factory
from qtpy.QtWidgets import QVBoxLayout, QWidget, QDockWidget

# from magicgui.widgets import Container
# if TYPE_CHECKING:
import napari

from ._segmentation_widget import SegmentationWidget
from ._tracking_widget import TrackingWidget
from ._intensity_plot import StepFinderWidget

class PluginWrapper(QWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.vbox_layout = QVBoxLayout()
        self.vbox_layout.setContentsMargins(0,0,0,0)
        self.vbox_layout.setSpacing(0)

        self.setLayout(self.vbox_layout)

        self.segmentation_widget = SegmentationWidget(napari_viewer=napari_viewer)
        self.vbox_layout.addWidget(self.segmentation_widget)
        # seg_dock = self.viewer.window.add_dock_widget(self.segmentation_widget, name="Segmentation")
        # seg_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable|QDockWidget.DockWidgetFeature.DockWidgetVerticalTitleBar)

        self.tracking_widget = TrackingWidget(napari_viewer=napari_viewer)
        self.vbox_layout.addWidget(self.tracking_widget)
        # track_dock = self.viewer.window.add_dock_widget(self.tracking_widget, name="Tracking")
        # track_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable|QDockWidget.DockWidgetFeature.DockWidgetVerticalTitleBar)

        # self.step_finder_widget = StepFinderWidget(napari_viewer=napari_viewer)
        # self.vbox_layout.addWidget(self.step_finder_widget)
        # step_dock = self.viewer.window.add_dock_widget(self.step_finder_widget, name="Plots")
        # step_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable|QDockWidget.DockWidgetFeature.DockWidgetVerticalTitleBar)

        # self.tracking_widget.track_selected.connect(self.step_finder_widget.set_track)