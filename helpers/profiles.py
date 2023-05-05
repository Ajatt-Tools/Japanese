# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import dataclasses
import enum


# noinspection PyArgumentList
@enum.unique
class PitchOutputFormat(enum.Enum):
    number = enum.auto()
    html = enum.auto()
    html_and_number = enum.auto()


@dataclasses.dataclass(frozen=True)
class Profile:
    name: str
    note_type: str
    source: str
    destination: str
    mode: str
    split_morphemes: bool

    _subclasses_map = {}  # "furigana" (str) -> ProfileFurigana

    def __init_subclass__(cls, **kwargs):
        mode = kwargs.pop('mode')  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[mode] = cls
        cls.mode = mode

    def __new__(cls, mode: str, *args, **kwargs):
        subclass = cls._subclasses_map[mode]
        return object.__new__(subclass)

    @classmethod
    def class_by_mode(cls, mode: str):
        return cls._subclasses_map[mode]

    @classmethod
    def new(cls, **kwargs):
        return cls(
            mode=cls.mode,
            name="New profile",
            note_type="Japanese",
            split_morphemes=True,
            **kwargs,
        )

    @classmethod
    def get_default(cls, mode: str):
        return cls.class_by_mode(mode).new()

    @classmethod
    def clone(cls, profile: 'Profile'):
        return cls(**dataclasses.asdict(profile))


@dataclasses.dataclass(frozen=True)
class ProfilePitch(Profile, mode="pitch"):
    output_format: str

    @classmethod
    def new(cls):
        return super().new(
            source="VocabKanji",
            destination="VocabPitchPattern",
            output_format=PitchOutputFormat.html.name,
        )


@dataclasses.dataclass(frozen=True)
class ProfileFurigana(Profile, mode="furigana"):
    @classmethod
    def new(cls):
        return super().new(
            source="VocabKanji",
            destination="VocabFurigana",
        )


@dataclasses.dataclass(frozen=True)
class ProfileAudio(Profile, mode="audio"):
    @classmethod
    def new(cls):
        return super().new(
            source="VocabKanji",
            destination="VocabAudio",
        )


def test():
    import json

    with open('../config.json') as f:
        config = json.load(f)

    for p in config.get('profiles'):
        print(Profile(**p))


if __name__ == '__main__':
    test()
