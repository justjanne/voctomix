import logging
from dataclasses import dataclass
from typing import Optional, Union

import gi

gi.require_version('GstController', '1.0')
from gi.repository import Gst, GstController
from vocto.transitions import Frame, L, T, R, B


@dataclass
class MixerPads:
    xpos: GstController.InterpolationControlSource
    ypos: GstController.InterpolationControlSource
    width: GstController.InterpolationControlSource
    height: GstController.InterpolationControlSource
    alpha: GstController.InterpolationControlSource
    zorder: GstController.InterpolationControlSource


@dataclass
class CropperPads:
    cropleft: GstController.InterpolationControlSource
    cropright: GstController.InterpolationControlSource
    croptop: GstController.InterpolationControlSource
    cropbottom: GstController.InterpolationControlSource


class Scene:
    """ Scene is the adaptor between the gstreamer compositor
        and voctomix frames.
        With commit() you add frames at a specified play time
    """
    log = logging.getLogger('Scene')
    frames: dict[str, Optional[list[Frame]]]
    mixer_pads: dict[str, MixerPads]
    cropper_pads: dict[str, CropperPads]
    dirty: bool

    def __init__(self, sources: list[str], pipeline: Gst.Pipeline, fps: float, start_sink: int, cropping: bool = True):
        """ initialize with a gstreamer pipeline and names
            of the sources to manage
        """
        # frames to apply from
        self.frames = dict[str, Optional[list[Frame]]]()
        # binding pads to apply to
        self.mixer_pads = dict()
        self.cropper_pads = dict() if cropping else None
        # time per frame
        self.frame_time = int(Gst.SECOND / fps)

        def bind(pad: Union[Gst.Pad, Gst.Element], prop: str) -> GstController.InterpolationControlSource:
            """ adds a binding to a gstreamer property
                pad's property
            """
            # set up a new control source
            cs = GstController.InterpolationControlSource()
            # stop control source's internal interpolation
            cs.set_property('mode', GstController.InterpolationMode.NONE)
            # create control binding
            cb = GstController.DirectControlBinding.new_absolute(pad, prop, cs)
            # add binding to pad
            pad.add_control_binding(cb)
            # return binding
            return cs

        # walk all sources
        videomixer = pipeline.get_by_name("videomixer")
        for idx, source in enumerate(sources):
            # initially invisible
            self.frames[source] = None
            # get mixer pad from pipeline
            mixerpad = videomixer.get_static_pad('sink_{}'.format(idx + start_sink))
            # add dictionary of binds to all properties
            # we vary for this source
            self.mixer_pads[source] = MixerPads(
                xpos=bind(mixerpad, 'xpos'),
                ypos=bind(mixerpad, 'ypos'),
                width=bind(mixerpad, 'width'),
                height=bind(mixerpad, 'height'),
                alpha=bind(mixerpad, 'alpha'),
                zorder=bind(mixerpad, 'zorder'),
            )
            # get mixer and cropper pad from pipeline
            if self.cropper_pads is not None:
                cropperpad = pipeline.get_by_name("cropper-{}".format(source))
                self.cropper_pads[source] = CropperPads(
                    croptop=bind(cropperpad, 'top'),
                    cropleft=bind(cropperpad, 'left'),
                    cropbottom=bind(cropperpad, 'bottom'),
                    cropright=bind(cropperpad, 'right'),
                )
        # ready to initialize gstreamer
        self.dirty = False

    def commit(self, source: str, frames: list[Frame]):
        """ commit multiple frames to the current gstreamer scene """
        self.log.debug("Commit %d frame(s) to source %s", len(frames), source)
        self.frames[source] = frames
        self.dirty = True

    def set(self, source: str, frame: Frame):
        """ commit single frame to the current gstreamer scene """
        self.log.debug("Set frame to source %s", source)
        self.frames[source] = [frame]
        self.dirty = True

    def push(self, at_time: int=0):
        """ apply all committed frames to GStreamer pipeline """
        # get pad for given source
        for source, frames in self.frames.items():
            if not frames:
                frames = [Frame(zorder=-1, alpha=0)]
            self.log.info(
                "Pushing %d frame(s) to source '%s' at time %dms",
                len(frames), source, at_time / Gst.MSECOND
            )
            # reset time
            time = at_time
            # get GStreamer property pad for this source
            mixer = self.mixer_pads[source]
            cropper = self.cropper_pads[source] if self.cropper_pads else None
            self.log.debug("    %s", Frame.str_title())
            # apply all frames of this source to GStreamer pipeline
            for idx, frame in enumerate(frames):
                self.log.debug("%2d: %s", idx, frame)
                cropped = frame.cropped()
                alpha = frame.float_alpha()
                # transmit frame properties into mixing pipeline
                mixer.xpos.set(time, cropped[L])
                mixer.ypos.set(time, cropped[T])
                mixer.width.set(time, cropped[R] - cropped[L])
                mixer.height.set(time, cropped[B] - cropped[T])
                mixer.alpha.set(time, alpha)
                mixer.zorder.set(time, frame.zorder if alpha != 0 else -1)
                if cropper:
                    cropper.croptop.set(time, frame.crop[T])
                    cropper.cropleft.set(time, frame.crop[L])
                    cropper.cropbottom.set(time, frame.crop[B])
                    cropper.cropright.set(time, frame.crop[R])
                # next frame time
                time += self.frame_time
            self.frames[source] = None
        self.dirty = False
