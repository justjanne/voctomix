import enum

from vocto.pipeline_element import PipelineTerminal


class PortDirection(enum.IntEnum):
    IN = 1
    OUT = 2

class Ports:
    NONE = 0

    OFFSET_PREVIEW = 100
    # core listening port
    CORE_LISTENING = 9999
    # input ports
    SOURCES_IN = 10000
    SOURCES_BACKGROUND = 16000
    SOURCE_OVERLAY= 14000
    SOURCES_BLANK = 17000
    AUDIO_SOURCE_BLANK = 18000
    # output ports
    MIX_OUT = 11000
    MIX_PREVIEW = MIX_OUT+OFFSET_PREVIEW
    SOURCES_OUT = 13000
    SOURCES_PREVIEW = SOURCES_OUT+OFFSET_PREVIEW
    LIVE_OUT = 15000
    LIVE_PREVIEW = LIVE_OUT+OFFSET_PREVIEW
    LOCALPLAYOUT_OUT = 19000

class Port:
    name: str
    port: any
    source: any
    audio: any
    video: any
    io: PortDirection
    connections: int

    def __init__(self, name: str, source: PipelineTerminal=None, audio=None, video=None):
        self.name = name
        self.source = source
        self.audio = audio
        self.video = video
        self.update()

    def to_dict(self) -> dict[str, any]:
        return {
            'name': self.name,
            'port': self.port,
            'audio': self.audio,
            'video': self.video,
            'io': self.io,
            'connections': self.connections
        }

    def update(self):
        if self.source:
            self.port = self.source.port()
            self.audio = self.source.audio_channels()
            self.video = self.source.video_channels()
            self.io = PortDirection.IN if self.source.is_input() else PortDirection.OUT
            self.connections = self.source.num_connections()

    @staticmethod
    def from_dict(_str: dict[str, any]) -> 'Port':
        p = Port(_str['name'])
        p.port = _str['port']
        p.audio = _str['audio']
        p.video = _str['video']
        p.io = _str['io']
        p.connections = _str['connections']
        return p

    def is_input(self) -> bool:
        return self.io == PortDirection.IN

    def is_output(self) -> bool:
        return self.io == PortDirection.OUT
