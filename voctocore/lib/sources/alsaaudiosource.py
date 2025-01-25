from typing import Optional

from voctocore.lib.config import Config
from voctocore.lib.sources.avsource import AVSource


class AlsaAudioSource(AVSource):
    device: str
    name: str

    def __init__(self, name: str, has_audio: bool = True, has_video: bool = False,
                 force_num_streams: Optional[int] = None):
        super().__init__('AlsaAudioSource', name, has_audio, has_video,
                         force_num_streams)
        self.device = Config.getAlsaAudioDevice(name)
        self.name = name

        self.build_pipeline()

    def port(self) -> str:
        return "AlsaAudio {}".format(self.device)

    def num_connections(self) -> int:
        return 1

    def __str__(self) -> str:
        return 'AlsaAudioSource[{name}] ({device})'.format(
            name=self.name,
            device=self.device
        )

    def build_audioport(self):
        return """alsasrc
                    name=alsaaudiosrc-{name}
                    device={device}
                  ! audioconvert
                  ! audioresample
                """.format(
            device=self.device,
            name=self.name,
        )

    def build_videoport(self) -> str:
        raise Exception("AlsaAudioSource has no video support")
