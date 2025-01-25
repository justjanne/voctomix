import re

from gi.repository import Gst

from voctocore.lib.config import Config
from voctocore.lib.sources.avsource import AVSource


class ImgVSource(AVSource):
    imguri: str

    pipeline: Gst.Pipeline

    def __init__(self, name: str):
        super().__init__('ImgVSource', name, False, True)
        self.imguri = Config.getImageURI(name)
        self.build_pipeline()

    def __str__(self) -> str:
        return 'ImgVSource[{name}] displaying {uri}'.format(
            name=self.name,
            uri=self.imguri
        )

    def port(self) -> str:
        m = re.search('.*/([^/]*)', self.imguri)
        return self.imguri

    def num_connections(self) -> int:
        return 1

    def video_channels(self) -> int:
        return 1

    def build_source(self) -> str:
        return """
            uridecodebin
                name=imgvsrc-{name}
                uri={uri}
            ! videoconvert
            ! imagefreeze
                name=img-{name}
        """.format(
            name=self.name,
            uri=self.imguri
        )

    def build_videoport(self) -> str:
        return "img-{name}.".format(name=self.name)

    def build_audioport(self) -> str:
        raise Exception("ImgVSource has no audio support")

    def restart(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.launch_pipeline()
