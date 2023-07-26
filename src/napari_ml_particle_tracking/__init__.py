__version__ = "0.0.1"
from ._widget import PluginWrapper

__all__ = (
    "PluginWrapper"
)

"""
# UI Plan

* Data = Image + Mask
* Mask Properties = Table with Mask Properties susch as [x, y, area, intensity, frame]
* Track Properties = Table with Track Properties susch as [x, y, area, intensity, frame, trackId]
* Track Meta Properties = Table [Track ID, number of time point, mean intensity, total number of steps, positive steps, negetive steps, [msd category]]
- Segmentation Widget
    - ML Infer Mask + Label + Mask Properties
    - Filter Mask based on Properties such as "Area"
    - Crop Data
    - Graph
        - Histogram Property

- Track Widget
    - Track Filter based on Track Meta Properties
        - Table view
    - Graph
        - Histogram of Meta Property
    
"""