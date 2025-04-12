# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.audio_manager.forvo_client import ForvoConfig, ForvoClient


def main():
    forvo_config = ForvoConfig()
    client = ForvoClient(forvo_config)
    result = client.word("清楚")
    for audio in result:
        print(audio)
    result = client.search("清楚")
    for audio in result:
        print(audio)


if __name__ == "__main__":
    main()
