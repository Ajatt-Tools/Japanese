import abc

from ..audio_manager.basic_types import FileUrlData


class AudioManagerHttpClientABC(abc.ABC):
    @abc.abstractmethod
    def download(self, file: FileUrlData) -> bytes:
        raise NotImplementedError()
