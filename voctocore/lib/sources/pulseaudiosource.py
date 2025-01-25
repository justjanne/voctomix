from voctocore.lib.config import Config
from voctocore.lib.sources.avsource import AVSource


class PulseAudioSource(AVSource):

    def __init__(self, name, has_audio=True, has_video=False,
                 force_num_streams=None):
        super().__init__('PulseAudioSource', name, has_audio, has_video,
                         force_num_streams)
        self.device = Config.getPulseAudioDevice(name)
        self.name = name

        self.build_pipeline()

    def port(self) -> str:
        return "PulseAudio {}".format(self.device)

    def num_connections(self) -> int:
        return 1

    def __str__(self) -> str:
        return 'PulseAudioSource[{name}] ({device})'.format(
            name=self.name,
            device=self.device
        )

    def build_audioport(self):
        # a volume of 0.126 is ~18dBFS
        return """pulsesrc
                    name=pulseaudiosrc-{name}
                    device={device}
                    client-name=voc2mix""".format(
            device=self.device,
            name=self.name,
        )

    def build_videoport(self) -> str:
        raise Exception("PulseAudioSource has no video support")
