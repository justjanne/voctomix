import logging

from gi.repository import Gst

from vocto.video_codecs import construct_video_encoder_pipeline
from voctocore.lib.args import Args
from voctocore.lib.avnode import AVIONode
from voctocore.lib.config import Config


class AVPreviewOutput(AVIONode):
    log: logging.Logger
    source: str
    bin: str
    listen_port: int
    connections: int

    def __init__(self, source: str, port: int, use_audio_mix: bool=False, audio_blinded: bool=False):
        # create logging interface
        if not hasattr(self, 'log'):
            self.log = logging.getLogger('AVPreviewOutput[{}]'.format(source))

        # remember things
        self.source = source
        self.listen_port = port
        self.connections = 0

        # open bin
        self.bin = "" if Args.no_bins else """
            bin.(
                name=AVPreviewOutput-{source}
                """.format(source=self.source)

        # video pipeline
        if source in Config.getVideoSources(internal=True):
            self.bin += """
                    video-{source}.
                    ! {vcaps}
                    ! queue
                        max-size-time=1
                        name=queue-preview-video-{source}
                    {vpipeline}
                    ! queue
                        max-size-time=1
                        name=queue-mux-preview-{source}
                    ! mux-preview-{source}.
                    """.format(source=self.source,
                               vpipeline=construct_video_encoder_pipeline(Config, 'previews'),
                               vcaps=Config.getVideoCaps()
                               )

        # audio pipeline
        if use_audio_mix or source in Config.getAudioSources(internal=True):
            self.bin += """
                    {use_audio}audio-{audio_source}{audio_blinded}.
                    ! queue
                        max-size-time=1
                        name=queue-preview-audio-{source}
                    ! audioconvert
                    ! queue
                        max-size-time=1
                        name=queue-mux-preview-audio-{source}
                    ! mux-preview-{source}.
                    """.format(source=self.source,
                               use_audio="" if use_audio_mix else "source-",
                               audio_source="mix" if use_audio_mix else self.source,
                               audio_blinded="-blinded" if audio_blinded else ""
                               )

        # playout pipeline
        self.bin += """
                matroskamux
                    name=mux-preview-{source}
                    streamable=true
                    writing-app=Voctomix-AVPreviewOutput
                ! queue
                    max-size-time={buffer}
                    name=queue-fd-preview-{source}
                ! srtsink
                    sync=true
                    mode=listener
                    wait-for-connection=false
                    uri=srt://:{port}
                    latency=10
                    name=fd-preview-{source}
                """.format(source=self.source, port=self.listen_port, buffer=1_000_000_000 // 25)

        # close bin
        self.bin += "" if Args.no_bins else "\n)\n"

    def audio_channels(self) -> int:
        return Config.getNumAudioStreams()

    def video_channels(self) -> int:
        return 1

    def is_input(self) -> bool:
        return False

    def __str__(self) -> str:
        return 'AVPreviewOutput[{}]'.format(self.source)

    def num_connections(self) -> int:
        return self.connections

    def port(self) -> str:
        return "127.0.0.1:{}".format(self.listen_port)

    def attach(self, pipeline: Gst.Pipeline):
        self.pipeline = pipeline
