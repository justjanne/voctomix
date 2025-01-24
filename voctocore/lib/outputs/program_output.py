import logging

from gi.repository import Gst

from vocto.pipeline_element import PipelineTerminal
from vocto.port import Ports, Port
from voctocore.lib.config import Config


class ProgramOutputSink(PipelineTerminal):
    log: logging.Logger
    source: str
    bin: str

    pipeline: Gst.Pipeline

    def __init__(self, source: str, port: Port, use_audio_mix: bool = False, audio_blinded: bool = False):
        # create logging interface
        self.log = logging.getLogger("ProgramOutputSink".format(source))

        # remember things
        self.source = source

        # open bin
        # self.bin = "" if Args.no_bins else """
        #    bin.(
        #        name=LocalUI
        #        """

        self.bin = ""
        # video pipeline
        self.bin += """
                video-mix.
                ! {vcaps}
                ! queue
                    max-size-time=3000000000
                    name=queue-mux-video-localui
                ! {videosink} sync=false
        """.format(
            source=self.source,
            vcaps=Config.getVideoCaps(),
            videosink=Config.getProgramOutputVideoSink(),
        )

        # audio pipeline
        if use_audio_mix or source in Config.getAudioSources(internal=True):
            self.bin += """
                {use_audio}audio-{audio_source}{audio_blinded}.
                ! queue
                    max-size-time=3000000000
                    name=queue-audio-mix-convert-{source}
                ! audioconvert
                ! queue
                    max-size-time=3000000000
                    name=queue-mux-audio-{source}
                ! audioresample
                ! {audiosink}
                """.format(
                source=self.source,
                use_audio="" if use_audio_mix else "source-",
                audio_source="mix" if use_audio_mix else self.source,
                audio_blinded="-blinded" if audio_blinded else "",
                audiosink=Config.getProgramOutputAudioSink(),
            )

        # close bin
        # self.bin += "" if Args.no_bins else "\n)\n"

    def port(self):
        return Ports.NONE

    def num_connections(self) -> int:
        return 0

    def audio_channels(self) -> int:
        return Config.getNumAudioStreams()

    def video_channels(self) -> int:
        return 1

    def is_input(self) -> bool:
        return False

    def __str__(self) -> str:
        return "ProgramOutputSink[{}]".format(self.source)

    def attach(self, pipeline: Gst.Pipeline):
        self.pipeline = pipeline
