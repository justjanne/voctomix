import logging

from gi.repository import Gst

from vocto.video_codecs import construct_video_encoder_pipeline
from voctocore.lib.args import Args
from voctocore.lib.avnode import AVIONode
from voctocore.lib.config import Config


class AVStreamOutput(AVIONode):
    log: logging.Logger
    source: str
    bin: str
    listen_port: int
    connections: int

    def __init__(self, source: str, port: int, use_audio_mix: bool=False, audio_blinded: bool=False):
        # create logging interface
        if not hasattr(self, 'log'):
            self.log = logging.getLogger('AVStreamOutput[{}]'.format(source))

        # remember things
        self.source = source
        self.listen_port = port
        self.connections = 0

        # open bin
        self.bin = "" if Args.no_bins else """
            bin.(
                name=AVStreamOutput-{source}
                """.format(source=self.source)

        # video pipeline
        if source in Config.getVideoSources(internal=True):
            self.bin += """
                    video-{source}.
                    ! {vcaps}
                    ! queue
                        leaky=downstream
                        max-size-time=1000000000
                        name=queue-stream-video-{source}
                    {vpipeline}
                    ! queue
                        max-size-time=3000000000
                        name=queue-mux-stream-{source}
                    ! mux-stream-{source}.
                    """.format(source=self.source,
                               vpipeline=construct_video_encoder_pipeline(Config, 'stream-'+self.source),
                               vcaps=Config.getVideoCaps()
                               )

        # audio pipeline
        if use_audio_mix or source in Config.getAudioSources(internal=True):
            self.bin += """
                    {use_audio}audio-{audio_source}{audio_blinded}.
                    ! queue
                        leaky=downstream 
                        max-size-time=1000000000
                        name=queue-stream-audio-{source}
                    ! audioconvert
                    ! queue
                        max-size-time=3000000000
                        name=queue-mux-stream-audio-{source}
                    ! mux-stream-{source}.
                    """.format(source=self.source,
                               use_audio="" if use_audio_mix else "source-",
                               audio_source="mix" if use_audio_mix else self.source,
                               audio_blinded="-blinded" if audio_blinded else ""
                               )

        # playout pipeline
        self.bin += """
                matroskamux
                    name=mux-stream-{source}
                    streamable=true
                    writing-app=Voctomix-AVStreamOutput
                ! queue
                    max-size-time=3000000000
                    name=queue-fd-stream-{source}
                ! srtsink
                    sync=true
                    mode=listener
                    wait-for-connection=false
                    uri=srt://:{port}
                    latency=10
                    name=fd-stream-{source}
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
        return 'AVStreamOutput[{}]'.format(self.source)

    def num_connections(self) -> int:
        return self.connections

    def port(self) -> str:
        return "127.0.0.1:{}".format(self.listen_port)

    def attach(self, pipeline: Gst.Pipeline):
        self.pipeline = pipeline
