import logging
from typing import Optional

import gi
from gi.repository import Gst, GstController

gi.require_version('GstController', '1.0')


class Overlay:
    log: logging.Logger = logging.getLogger('Overlay')

    overlay: Gst.Element
    location: Optional[str]
    isVisible: bool
    blend_time: int
    alpha: GstController.InterpolationControlSource

    def __init__(self, pipeline: Gst.Pipeline, location: Optional[str] = None, blend_time: int = 300):
        # get overlay element and config
        self.overlay = pipeline.get_by_name('overlay')
        self.location = location
        self.isVisible = location is not None
        self.blend_time = blend_time

        # initialize overlay control binding
        self.alpha = GstController.InterpolationControlSource()
        self.alpha.set_property('mode', GstController.InterpolationMode.LINEAR)
        cb = GstController.DirectControlBinding.new_absolute(self.overlay, 'alpha', self.alpha)
        self.overlay.add_control_binding(cb)

    def set(self, location: str):
        self.location = location if location else ""
        if self.isVisible:
            self.overlay.set_property('location', self.location)

    def show(self, visible: bool, playtime: int):
        """ set overlay visibility """
        # check if control binding is available
        assert self.alpha
        # if state changes
        if self.isVisible != visible:
            # set blending animation
            if self.blend_time > 0:
                self.alpha.set(playtime, 0.0 if visible else 1.0)
                self.alpha.set(playtime + int(Gst.SECOND / 1000.0 * self.blend_time), 1.0 if visible else 0.0)
            else:
                self.alpha.set(playtime, 1.0 if visible else 0.0)
            # set new visibility state
            self.isVisible = visible
            # re-set location if we get visible
            if visible:
                self.overlay.set_property('location', self.location)

    def get(self) -> str:
        """ get current overlay file location """
        return self.location

    def visible(self) -> bool:
        """ get overlay visibility """
        return self.isVisible
