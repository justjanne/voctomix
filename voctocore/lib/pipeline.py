import logging
import re
import sys
from typing import cast

from gi.repository import Gst

from vocto.debug import gst_generate_dot
from vocto.pipeline_element import PipelineElement
from vocto.port import Port, Ports
from vocto.pretty import pretty
from voctocore.lib.args import Args
from voctocore.lib.audiomix import AudioMix
from voctocore.lib.blinder import Blinder
from voctocore.lib.clock import Clock
from voctocore.lib.config import Config
from voctocore.lib.outputs.avpreviewoutput import AVPreviewOutput
from voctocore.lib.outputs.avrawoutput import AVRawOutput
from voctocore.lib.outputs.program_output import ProgramOutputSink
from voctocore.lib.sources import spawn_source
from voctocore.lib.videomix import VideoMix


class Pipeline(object):
    """mixing, streaming and encoding pipeline constuction and control"""
    log: logging.Logger
    bin: list[PipelineElement]
    ports: list[Port]
    queues: list[Gst.Element]
    pipeline: Gst.Pipeline

    def __init__(self):
        self.log = logging.getLogger('Pipeline')
        # log capabilities
        self.log.info('Video-Caps configured to: %s', Config.getVideoCaps())
        self.log.info('Audio-Caps configured to: %s', Config.getAudioCaps())

        # get A/B sources from config
        sources = Config.getSources()
        if len(sources) < 1:
            raise RuntimeError("At least one AVSource must be configured!")

        # collect bins for all modules
        self.bins = []
        self.ports = []

        # create A/V sources
        self.log.info('Creating %u AVSources: %s', len(sources), sources)
        for idx, source_name in enumerate(sources):
            # count port and create source
            source = spawn_source(source_name, Ports.SOURCES_IN + idx)
            self.bins.append(source)
            self.ports.append(Port(source_name, source))

            if Config.getMirrorsEnabled():
                if source_name in Config.getMirrorsSources():
                    dest = AVRawOutput(source_name, Ports.SOURCES_OUT + idx)
                    self.bins.append(dest)
                    self.ports.append(Port(source_name, dest))

            # check for source preview selection
            if Config.getPreviewsEnabled():
                # count preview port and create source
                dest = AVPreviewOutput(source_name, Ports.SOURCES_PREVIEW + idx)
                self.bins.append(dest)
                self.ports.append(Port("preview-%s" % source_name, dest))

        # initialize audio streams
        Config.getAudioStreams()

        # create audio mixer
        self.log.info('Creating Audiomixer')
        self.amix = AudioMix()
        self.bins.append(self.amix)

        # create video mixer
        self.log.info('Creating Videomixer')
        self.vmix = VideoMix()
        self.bins.append(self.vmix)

        for idx, background in enumerate(Config.getBackgroundSources()):
            # create background source
            source = spawn_source(
                background, Ports.SOURCES_BACKGROUND + idx, has_audio=False)
            self.bins.append(source)
            self.ports.append(Port(background, source))

        # create mix TCP output
        if Config.getAVRawOutputEnabled():
            dest = AVRawOutput('mix', Ports.MIX_OUT, use_audio_mix=True)
            self.bins.append(dest)
            self.ports.append(Port('mix', dest))

        # add localui
        if Config.getProgramOutputEnabled():
            pgmout = ProgramOutputSink("mix", Ports.MIX_OUT, use_audio_mix=True)
            self.bins.append(pgmout)
            self.ports.append(Port('mix', pgmout))

        # create mix preview TCP output
        if Config.getPreviewsEnabled():
            dest = AVPreviewOutput('mix', Ports.MIX_PREVIEW, use_audio_mix=True)
            self.bins.append(dest)
            self.ports.append(Port('preview-mix', dest))

        # create blinding sources and mixer
        if Config.getBlinderEnabled():
            sources = Config.getBlinderSources()
            if len(sources) < 1:
                raise RuntimeError('At least one Blinder-Source must '
                                   'be configured or the '
                                   'Blinder disabled!')
            if Config.isBlinderDefault():
                source = spawn_source('blinder', Ports.SOURCES_BLANK)
                self.bins.append(source)
                self.ports.append(Port('blinder', source))
            else:
                for idx, source_name in enumerate(sources):
                    source = spawn_source(source_name,
                                          Ports.SOURCES_BLANK + idx,
                                          has_audio=False)
                    self.bins.append(source)
                    self.ports.append(Port('blinded-{}'.format(source_name), source))

                source = spawn_source('blinder', Ports.AUDIO_SOURCE_BLANK, has_video=False)
                self.bins.append(source)
                self.ports.append(Port('blinder-audio', source))

            self.log.info('Creating Blinder')
            self.blinder = Blinder()
            self.bins.append(self.blinder)

            # check for source preview selection
            if Config.getPreviewsEnabled():
                for idx, livepreview in enumerate(Config.getLivePreviews()):
                    dest = AVPreviewOutput('{}-blinded'.format(livepreview), Ports.LIVE_PREVIEW + idx,
                                           use_audio_mix=True, audio_blinded=True)
                    self.bins.append(dest)
                    self.ports.append(Port('preview-{}-blinded'.format(livepreview), dest))

            for idx, livesource in enumerate(Config.getLiveSources()):
                dest = AVRawOutput('{}-blinded'.format(livesource), Ports.LIVE_OUT + idx, use_audio_mix=True,
                                   audio_blinded=True)
                self.bins.append(dest)
                self.ports.append(Port('{}-blinded'.format(livesource), dest))

        # TODO test after 2.0 is released
        # if Config.getLocalRecordingEnabled():
        #    playout = LocalRecordingSink('mix', Ports.LOCALPLAYOUT_OUT, use_audio_mix=True, audio_blinded=True)
        #    self.bins.append(playout)
        #    self.ports.append(Port('{}-playout'.format("mix"), playout))

        # TODO test after 2.0 is released
        # if Config.getSRTServerEnabled():
        #    playout = SRTServerSink('mix', Ports.LOCALPLAYOUT_OUT, use_audio_mix=True, audio_blinded=True)
        #    self.bins.append(playout)
        #    self.ports.append(Port('{}-playout'.format("mix"), playout))

        for _bin in self.bins:
            self.log.info("%s\n%s", _bin, pretty(_bin.bin))

        # concatenate pipeline string
        pipeline = "\n\n".join(bin.bin for bin in self.bins)

        if Args.pipeline:
            with open("core.pipeline.txt", "w") as file:
                file.write(pretty(pipeline))

        self.prevstate = None
        try:
            # launch gstreamer pipeline
            self.pipeline = cast(Gst.Pipeline, Gst.parse_launch(pipeline))
            self.log.info("pipeline launched successfuly")
        except Exception:
            self.log.exception("Can not launch pipeline")
            sys.exit(-1)

        # attach pads
        for bin in self.bins:
            bin.attach(self.pipeline)

        self.pipeline.use_clock(Clock)

        # fetch all queues
        self.queues = self.fetch_elements_by_name(r'^queue-[\w_-]+$')

        self.log.debug('Binding End-of-Stream-Signal on Source-Pipeline')
        self.pipeline.bus.add_signal_watch()
        self.pipeline.bus.connect("message::eos", self.on_eos)
        self.pipeline.bus.connect("message::error", self.on_error)
        self.pipeline.bus.connect("message::state-changed", self.on_state_changed)

        self.pipeline.set_state(Gst.State.PLAYING)

    def fetch_elements_by_name(self, regex: str):
        # fetch all watchdogs
        result = []

        def query(element):
            if re.match(regex, element.get_name()):
                result.append(element)

        self.pipeline.iterate_recurse().foreach(query)
        return result

    def on_eos(self, bus, message: Gst.Message):
        self.log.debug('Received End-of-Stream-Signal on Source-Pipeline')

    def on_error(self, bus, message: Gst.Message):
        error, debug = message.parse_error()
        self.log.debug(debug)
        self.log.error("GStreamer pipeline element '%s' signaled an error #%u: %s" % (message.src.name, error.code, error.message) )
        sys.exit(-1)

    def on_state_changed(self, bus, message: Gst.Message):
        newstate = message.parse_state_changed().newstate
        states = ["PENDING", "NULL", "READY", "PAUSED", "PLAYING"]
        self.log.debug("element state changed to '%s' by element '%s'", states[newstate], message.src.name)
        if self.prevstate != newstate and message.src.name == "pipeline0":
            self.prevstate = newstate
            self.log.debug("pipeline state changed to '%s'", states[newstate])
            if newstate == Gst.State.PLAYING:
                self.log.info("\n\n====================== UP AND RUNNING =====================\n")

            if Args.dot or Args.gst_debug_details:
                # make DOT file from pipeline
                gst_generate_dot(self.pipeline, "core.pipeline", int(Args.gst_debug_details))
