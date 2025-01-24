import abc
from abc import abstractmethod
from gi.repository import Gst

class PipelineElement(abc.ABC):
    @abstractmethod
    def attach(self, pipeline: Gst.Pipeline):
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass

class PipelineTerminal(PipelineElement, metaclass=abc.ABCMeta):
    @abstractmethod
    def audio_channels(self) -> int:
        pass

    @abstractmethod
    def video_channels(self) -> int:
        pass

    @abstractmethod
    def is_input(self) -> bool:
        pass

    @abstractmethod
    def num_connections(self) -> int:
        pass

    @abstractmethod
    def port(self) -> str:
        pass
