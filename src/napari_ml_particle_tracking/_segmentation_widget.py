import os
import sys
from pathlib import Path

import numpy as np
import napari
from napari.utils import progress

from qtpy.QtWidgets import QPushButton, QHBoxLayout, QSpinBox
from ._base_widget import NapariLayersWidget


from pathlib import Path

_MODEL_FILE_NAME_ = 'model_final.pt'
_MODEL_DIR_ = Path.home().joinpath('.ml_particle_tracking')
_MODEL_FILE_PATH_ = _MODEL_DIR_.joinpath(_MODEL_FILE_NAME_)


    
class SegmentationWidget(NapariLayersWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__(napari_viewer)
        
        
        self.sb_epochs = QSpinBox()
        self.btn_segment = QPushButton("Generate Mask")
        self.btn_train = QPushButton("Re-Train")

        # { TODO: update late 
        # self.btn_train.setVisible(False)
        # self.sb_epochs.setVisible(False)
        #### }

        self.layout().addRow("Number of Epochs", self.sb_epochs)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_segment)
        btn_layout.addWidget(self.btn_train)
        
        
        self.layout().addRow(btn_layout)

        # init widget
        # disable the train buttnon and sb_epochs if there is no mask layer

        self.sb_epochs.setValue(10)
        self.sb_epochs.setMinimum(1)
        self.sb_epochs.setDisabled(True)
        self.btn_train.setDisabled(True)

        # init btns
        self.btn_segment.clicked.connect(self.segment)
        self.btn_train.clicked.connect(self.train)

        self.update_btns()
        self.comboBoxUpdated.connect(self.update_btns)
        
        # inti ml
        self.init_ml()

    
    def update_btns(self):
        
        if self.combo_image_layers.count():
            self.btn_segment.setDisabled(False)
        else:
            self.btn_segment.setDisabled(True)

        if self.combo_mask_layers.count():
            self.sb_epochs.setDisabled(False)
            self.btn_train.setDisabled(False)
        else:
            self.sb_epochs.setDisabled(True)
            self.btn_train.setDisabled(True)
    
    def init_ml(self):
        from particle_tracking import Model, Data2D, Dataset2D
        from torch import nn, optim
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
        image_layer = self.viewer.layers[image_layer_index].data

        pred = np.zeros_like(image_layer, dtype=np.uint8)
        for i in progress(range(image_layer.shape[0]), desc="Inference Loop"):
            mask = self.model.inference(image_layer[i])
            pred[i] = mask.astype(np.uint8)

        self.viewer.add_labels(pred, name="Mask")

    def train(self):
        # make sure train button is set to visible
        pass
    
