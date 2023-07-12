from typing import TYPE_CHECKING
import numpy as np
from magicgui import magic_factory
from qtpy.QtWidgets import QVBoxLayout, QPushButton, QWidget, QFormLayout, QComboBox, QHBoxLayout, QSpinBox, QTableView
from qtpy.QtGui import QStandardItemModel
from qtpy.QtCore import Signal
# from magicgui.widgets import Container
from pathlib import Path


# if TYPE_CHECKING:
import napari
from napari.utils import progress

_MODEL_FILE_NAME_ = 'model_final.pt'
_MODEL_DIR_ = Path.home().joinpath('.ml_particle_tracking')
_MODEL_FILE_PATH_ = _MODEL_DIR_.joinpath(_MODEL_FILE_NAME_)


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
    
class SegmentationWidget(NapariLayersWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__(napari_viewer)
        
        
        self.sb_epochs = QSpinBox()
        self.btn_segment = QPushButton("Generate Mask")
        self.btn_train = QPushButton("Re-Train")

        # { TODO: update late 
        self.btn_train.setVisible(False)
        self.sb_epochs.setVisible(False)
        #### }

        self.layout().addRow("Number of Epochs", self.sb_epochs)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_segment)
        btn_layout.addWidget(self.btn_train)
        
        
        self.layout().addWidget(btn_layout)

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
    


class TrackingWidget(NapariLayersWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__(napari_viewer)

        self.btn_track = QPushButton("Track")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_track)

        self.layout().addWidget(btn_layout)

        self.table = QTableView()
        self.table_model = QStandardItemModel()
        self.table.setModel(self.table_model)
        
        self.layout().addWidget(self.table)

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
        tracked = get_tracks(main_pd_frame)

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

class PluginWrapper(QWidget):
    def __init__(self, napari_viewer : napari.viewer.Viewer):
        super().__init__()
        self.vbox_layout = QVBoxLayout()
        self.vbox_layout.setContentsMargins(0,0,0,0)
        self.vbox_layout.setSpacing(0)
        self.setLayout(self.vbox_layout)

        self.segmentation_widget = SegmentationWidget(napari_viewer=napari_viewer)
        self.vbox_layout.addWidget(self.segmentation_widget)

