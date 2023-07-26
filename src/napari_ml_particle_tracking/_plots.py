import os
import sys
from pathlib import Path
from typing import Optional
import numpy as np
import tifffile
import matplotlib
from typing import Optional
from matplotlib.backends.backend_qtagg import (
    FigureCanvas,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget


colors = dict(
    COLOR_1 = "#DC267F",
    COLOR_2 = "#648FFF",
    COLOR_3 = "#785EF0",
    COLOR_4 = "#FE6100",
    COLOR_5 = "#FFB000")

class BaseMPLWidget(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)

        
        self.canvas = FigureCanvas()
        self.toolbar = NavigationToolbar2QT(
            self.canvas, parent=self
        )

        self.canvas.figure.set_layout_engine("constrained")
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

    @property
    def figure(self) -> Figure:
        """Matplotlib figure."""
        return self.canvas.figure


    def add_single_axes(self) -> None:
        """
        Add a single Axes to the figure.

        The Axes is saved on the ``.axes`` attribute for later access.
        """
        self.axes = self.figure.subplots()



class HistogramWidget(BaseMPLWidget):
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)

        # self._setup_callbacks()
        self.add_single_axes()
        self.data = []
        self.label = None
        self.color = None

    def clear(self) -> None:
        """
        Clear any previously drawn figures.

        This is a no-op, and is intended for derived classes to override.
        """
        self.axes.clear()

    def draw(self, data, label, bins=256, color=colors['COLOR_1']) -> None:
        self.clear()
        if len(data):
            self.data = data
            self.label = label
            self.color = color
            y = np.array(self.data)
            # self.axes.plot(x, self.data, label =label, color=color)
            # self.axes.hist(data.ravel(), bins=bins, label=layer.name)
            self.axes.hist(y.ravel(), bins=bins, label=label)
            self.axes.legend(loc='upper right')

        # needed
        self.canvas.draw()
########################################