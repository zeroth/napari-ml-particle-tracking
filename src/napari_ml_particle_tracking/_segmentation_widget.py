import os
import sys
from pathlib import Path

import numpy as np
import napari
from napari.utils import progress

from qtpy.QtWidgets import QPushButton, QHBoxLayout, QSpinBox, QCheckBox, QFileDialog, QMessageBox
from qtpy.QtCore import Qt
from ._base_widget import NapariLayersWidget
from pathlib import Path
import tifffile

from particle_tracking import Model, Data2D, Dataset2D
from torch import nn, optim

_MODEL_FILE_NAME_ = 'model_final.pt'
_MODEL_DIR_ = Path.home().joinpath('.ml_particle_tracking')
_MODEL_FILE_PATH_ = _MODEL_DIR_.joinpath(_MODEL_FILE_NAME_)


    
class SegmentationWidget(NapariLayersWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__(napari_viewer)
        
        
        self.sb_epochs = QSpinBox()
        self.cb_use_entire_mask = QCheckBox()
        self.cb_use_entire_mask.setCheckState(Qt.CheckState.Checked)
        self.btn_segment = QPushButton("Generate Mask")
        self.btn_train = QPushButton("Re-Train")

        # { TODO: update late 
        # self.btn_train.setVisible(False)
        # self.sb_epochs.setVisible(False)
        #### }

        self.layer_layout.addRow("Number of Epochs", self.sb_epochs)
        self.layer_layout.addRow("Use entire mask to retrain", self.cb_use_entire_mask)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_segment)
        btn_layout.addWidget(self.btn_train)
        
        
        self.layout().addLayout(btn_layout)

        # init widget
        # disable the train buttnon and sb_epochs if there is no mask layer

        self.sb_epochs.setValue(10)
        self.sb_epochs.setMinimum(1)
        self.sb_epochs.setDisabled(True)
        self.btn_train.setDisabled(True)

        # init btns
        self.open_action.setVisible(False)
        self.save_action.setDisabled(True)
        self.saveClicked.connect(self.save)
        self.btn_segment.clicked.connect(self.segment)
        self.btn_train.clicked.connect(self.train)

        self.update_btns()
        self.comboBoxUpdated.connect(self.update_btns)
        self.comboBoxUpdated.connect(self.attach_mask_layer)
        
        # inti ml
        self.init_ml()

        self.mask_layer = None
        self.image_layer = None
        self.training_image = None
        self.training_mask = None
        self.change_indices = set()

    
    def update_btns(self):
        
        if self.combo_image_layers.count():
            self.btn_segment.setDisabled(False)
        else:
            self.btn_segment.setDisabled(True)

        if self.combo_mask_layers.count():
            self.sb_epochs.setDisabled(False)
            self.btn_train.setDisabled(False)
            self.save_action.setDisabled(False)
        else:
            self.sb_epochs.setDisabled(True)
            self.btn_train.setDisabled(True)
            self.save_action.setDisabled(True)
    
    def init_ml(self):
        n_epochs = self.sb_epochs.value()
        learning_rate = 1.e-4
        train_test_split = 0.7
        loss_function  = nn.BCEWithLogitsLoss()

        # data = Data2D(image_layer, mask)

        # dataset = Dataset2D(data.images, data.labels)
        # train_dataloader, test_dataloader, acc_dataloader = dataset.get_data_loader(split=train_test_split)
        self.model = Model(
                    pre_trained_model_path=_MODEL_FILE_PATH_,
                    optimizerCls=optim.Adam,
                    learning_rate = learning_rate,
                    loss_fn=loss_function,
                    encoder_name="resnet18", 
                    encoder_weights="imagenet",
                    in_channels = 1, 
                    classes=1,
                    is_inference_mode=True
                )

    def segment(self):
        image_layer_index = self.combo_image_layers.currentData()
        self.image_layer = self.viewer.layers[image_layer_index]
        image_data = self.image_layer.data

        pred = np.zeros_like(image_data, dtype=np.uint8)
        for i in progress(range(image_data.shape[0]), desc="Inference Loop"):
            mask = self.model.inference(image_data[i])
            pred[i] = mask.astype(np.uint8)

        if self.combo_mask_layers.count():
            mask_layer_index = self.combo_mask_layers.currentData()
            self.mask_layer = self.viewer.layers[mask_layer_index]
            self.mask_layer.data = pred
        else:
            self.viewer.add_labels(pred, name="Mask")

    def train(self):
        # prepare data
        if self.cb_use_entire_mask.checkState() == Qt.CheckState.Unchecked:
            indices = list(self.change_indices)
            self.training_image = self.image_layer.data[indices]
            self.training_mask = self.mask_layer.data[indices]
        else:
            self.training_image = self.image_layer.data
            self.training_mask = self.mask_layer.data

        _data = Data2D(self.training_image, self.training_mask)
        _dataset = Dataset2D(_data.images, _data.labels)
        _dataloader = _dataset.get_single_data_loader()
        n_epochs = self.sb_epochs.value()
        for epoch in progress(range(n_epochs), desc="Training"):
            self.model.train(True)
            self.model.train_one_epoch(_dataloader, epoch_index=epoch)
        
        self.model.save(_MODEL_FILE_PATH_)
        print("training done- segmenting")
        self.segment()
        
    
    def training_data_collection(self, layer, event):
        # print(f"Mouse clicked : {layer.name} -> {event.position}")
        self.change_indices.add( int(event.position[0]))

    def attach_mask_layer(self):
        if self.combo_mask_layers.count():
            mask_layer_index = self.combo_mask_layers.currentData()
            self.mask_layer = self.viewer.layers[mask_layer_index]
            self.mask_layer.mouse_drag_callbacks.append(self.training_data_collection)

        if self.combo_image_layers.count():
            mask_image_index = self.combo_image_layers.currentData()
            self.image_layer = self.viewer.layers[mask_image_index]

    def save(self):
        file_path = QFileDialog.getSaveFileName(self, caption="Save Mask", directory=str(Path.home()), filter="*.tif")
        if self.combo_mask_layers.count():
            mask_layer_index = self.combo_mask_layers.currentData()
            self.mask_layer = self.viewer.layers[mask_layer_index]
            tifffile.imwrite(file=file_path[0], data=self.mask_layer.data.astype(np.uint8))
        else:
            QMessageBox.warning(self, "Save error", "No mask layer available to save.\nMake sure you have 'Mask' Layer by clicking on 'Generate Mask'. ")
            
    
