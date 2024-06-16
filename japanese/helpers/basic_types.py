import abc


class AudioManagerHttpClientABC(abc.ABC):
    @abc.abstractmethod
    def download(self, file):
        raise NotImplementedError()
