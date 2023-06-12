"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING
import numpy as np
from magicgui import magic_factory
from qtpy.QtWidgets import QVBoxLayout, QPushButton, QWidget, QFormLayout, QComboBox, QLayout
# from magicgui.widgets import Container

# if TYPE_CHECKING:
import napari

@magic_factory (
        call_button="Run",
        extra_button = dict(widget_type='PushButton', enabled=False, label='Train')
)
def ml_interaction(image_layer: "napari.types.ImageData", 
                   mask:"napari.types.LabelsData", 
                   n_epochs:int=10, extra_button=True) -> "napari.types.LabelsData":
    if image_layer:
        from particle_tracking import Model, Data2D, Dataset2D
        from torch import nn, optim
        n_epochs = n_epochs
        learning_rate = 1.e-4
        train_test_split = 0.7
        loss_function  = nn.BCEWithLogitsLoss()

        data = Data2D(image_layer, mask)

        dataset = Dataset2D(data.images, data.labels)
        train_dataloader, test_dataloader, acc_dataloader = dataset.get_data_loader(split=train_test_split)

        model = Model(pre_trained_model_path='./data/chckpoint.tp', 
                    optimizerCls=optim.Adam, 
                    learning_rate=learning_rate, 
                    loss_fn=loss_function,
                    train_dataloader=train_dataloader,
                    validation_dataloader=test_dataloader,
                    acc_dataloader=acc_dataloader
                )
        
        return model.inference(image_layer)
        # zeros = np.zeros(image_layer.shape, dtype='uint16')
        # zeros[:, 10:20, 20:30] = 255
        # return zeros

class MlInteractionQWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        btn = QPushButton("Click me!")
        btn.clicked.connect(self._on_click)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(btn)
        napari_viewer.layers.events.changed.connect(self._test)
        napari_viewer.layers.events.inserted.connect(self._test2)

    def _on_click(self):
        print("napari has", len(self.viewer.layers), "layers")
        img_layer = self.viewer.layers[0].data
        zeros = np.zeros(img_layer.shape, dtype='uint16')
        zeros[10:20, 20:30] = 255
        self.viewer.add_labels(zeros)

    def _test(self):
        print("test")
    
    def _test2(self):
        
        for l in self.viewer.layers:
            print(type(l))
            print("-----------")
            print("dtype", l.dtype)
            if isinstance(l, napari.layers.Image):
                print("this is image")
            if isinstance(l, napari.layers.Labels):
                print("this is Labels")
            
            



# @magic_factory
# def example_magic_widget(img_layer: "napari.layers.Image"):
#     print(f"you have selected {img_layer}")


# # Uses the `autogenerate: true` flag in the plugin manifest
# # to indicate it should be wrapped as a magicgui to autogenerate
# # a widget.
# def example_function_widget(img_layer: "napari.layers.Image"):
#     print(f"you have selected {img_layer}")
