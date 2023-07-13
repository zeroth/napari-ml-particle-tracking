import napari
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QFormLayout, QComboBox

class NapariLayersWidget(QWidget):
    comboBoxUpdated = Signal()
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        
        layout = QFormLayout(self)
        self.setLayout(layout)

        self.combo_image_layers = QComboBox()
        self.combo_mask_layers = QComboBox()
        
        layout.addRow("Image Layer", self.combo_image_layers)
        layout.addRow("Mask Layer", self.combo_mask_layers)
                
        # init the layers
        self.update_combo()

        # connect
        self.viewer.layers.events.changed.connect(self.update_combo)
        self.viewer.layers.events.inserted.connect(self.update_combo)
        self.viewer.layers.events.removed.connect(self.update_combo)
        self.viewer.layers.events.moved.connect(self.update_combo)

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