import typing
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
import napari
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QFormLayout, QComboBox, QVBoxLayout, QToolBar, QStyle,QSizePolicy

class BaseWidget(QWidget):
    saveClicked = Signal()
    openClicked = Signal()
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.toolBar = QToolBar("Controls")
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # toolBar is a pointer to an existing toolbar
        self.toolBar.addWidget(spacer)
        self.open_action  = self.toolBar.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Open")
        self.save_action  = self.toolBar.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save")
        self.save_action.triggered.connect(self.saveClicked)
        self.open_action.triggered.connect(self.openClicked)
        self.layout().addWidget(self.toolBar)

class NapariLayersWidget(BaseWidget):
    comboBoxUpdated = Signal()
    def __init__(self, napari_viewer : napari.viewer.Viewer=None, parent:QWidget=None):
        super().__init__(parent)
        self.viewer = napari_viewer
        
        self.layer_layout = QFormLayout()
        self.layout().addLayout(self.layer_layout)

        self.combo_image_layers = QComboBox()
        self.combo_mask_layers = QComboBox()
        
        self.layer_layout.addRow("Image Layer", self.combo_image_layers)
        self.layer_layout.addRow("Mask Layer", self.combo_mask_layers)
                
        # init the layers
        if self.viewer != None:
            self.update_combo()

        # connect
        if self.viewer != None:
            self.viewer.layers.events.changed.connect(self.update_combo)
            self.viewer.layers.events.inserted.connect(self.update_combo)
            self.viewer.layers.events.removed.connect(self.update_combo)
            self.viewer.layers.events.moved.connect(self.update_combo)

        self.combo_image_layers.currentIndexChanged.connect(self.comboBoxUpdated)
        self.combo_mask_layers.currentIndexChanged.connect(self.comboBoxUpdated)

    def update_combo(self):
        self.combo_image_layers.clear()
        self.combo_mask_layers.clear()
        for i, l in enumerate(self.viewer.layers):
            if isinstance(l, napari.layers.Image):
                self.combo_image_layers.addItem(l.name, i)
            if isinstance(l, napari.layers.Labels):
                self.combo_mask_layers.addItem(l.name, i)
        
        self.comboBoxUpdated.emit()
    
    def show_mask(self, state):
        layer_name = self.combo_mask_layers.currentText()
        self.viewer.layers[layer_name].visible = state
    
    def show_image(self, state):
        layer_name = self.combo_image_layers.currentText()
        self.viewer.layers[layer_name].visible = state


if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = NapariLayersWidget()
    w.show()
    app.exec_()