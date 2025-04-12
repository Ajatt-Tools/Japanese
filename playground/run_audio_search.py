# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import random
import string

from aqt.qt import *

from japanese.audio_manager.abstract import AnkiAudioSourceManagerABC
from japanese.audio_manager.basic_types import FileUrlData
from japanese.audio_manager.forvo_client import ForvoClient, ForvoConfig
from japanese.widgets.audio_search import AudioSearchDialog


def gen_rand_str(length: int = 10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_rand_file() -> FileUrlData:
    return FileUrlData(
        url=f"https://example.com/{gen_rand_str()}.ogg",
        desired_filename=f"{gen_rand_str()}.ogg",
        word=gen_rand_str(),
        reading="あいうえお",
        source_name=f"src{gen_rand_str()}",
    )


class NoAnkiAudioSourceManager(AnkiAudioSourceManagerABC):
    # noinspection PyMethodMayBeStatic
    # noinspection PyUnusedLocal
    def search_audio(self, src_text: str, **kwargs) -> list[FileUrlData]:
        """
        Used for testing purposes.
        """
        output = []
        if src_text:
            for _ in range(random.randint(1, 10)):
                output.append(get_rand_file())
        return output

    def download_and_save_tags(self, *args):
        pass


def main():
    app = QApplication(sys.argv)
    dialog = AudioSearchDialog(NoAnkiAudioSourceManager(), ForvoClient(config=ForvoConfig()))
    dialog.set_note_fields(
        [
            "Question",
            "Answer",
            "Audio",
            "Image",
        ],
        selected_dest_field_name="Audio",
        selected_src_field_name="Question",
    )
    dialog.search("清楚")
    dialog.show()
    app.exec()
    print("chosen:")
    for file in dialog.files_to_add():
        print(file)
    print(f"source: {dialog.source_field_name}")
    print(f"destination: {dialog.destination_field_name}")


if __name__ == "__main__":
    main()
