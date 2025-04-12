# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.audio_manager.forvo_client import ForvoClient, ForvoConfig


def main():
    forvo_config = ForvoConfig()
    client = ForvoClient(forvo_config)
    result = client.full_search("清楚")
    print(f"search error: {result.error_search}")
    print(f"word error: {result.error_word}")
    for audio in result.files:
        print(audio)


if __name__ == "__main__":
    main()
