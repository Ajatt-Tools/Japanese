# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
import typing

from .consts import CFG_WORD_SEP


@enum.unique
class PitchOutputFormat(enum.Enum):
    number = enum.auto()
    html = enum.auto()
    html_and_number = enum.auto()
    svg = enum.auto()


@enum.unique
class ColorCodePitchFormat(enum.Flag):
    attributes = enum.auto()
    color = enum.auto()
    underline = enum.auto()


@dataclasses.dataclass(frozen=True)
class TaskCallerOpts:
    audio_download_report: bool = True


@enum.unique
class TaskCaller(enum.Flag):
    focus_lost = enum.auto()
    toolbar_button = enum.auto()
    note_added = enum.auto()
    bulk_add = enum.auto()

    @property
    def cfg(self) -> TaskCallerOpts:
        if self == self.bulk_add:
            return TaskCallerOpts(audio_download_report=False)
        return TaskCallerOpts()

    @classmethod
    def all_enabled(cls):
        flag = cls(0)
        for add in cls:
            flag |= add
        return flag


class AnkiNoteProtocol(typing.Protocol):
    def __contains__(self, key: str) -> bool: ...


class ProfileBase:
    _subclasses_map: dict[str, type["Profile"]] = {}  # "furigana" (str) -> ProfileFurigana


def get_common_keys(d1: dict, d2: dict):
    return d1.keys() & d2.keys()


@dataclasses.dataclass(frozen=True)
class Profile(ProfileBase):
    name: str
    note_type: str
    source: str
    destination: str
    mode: str
    split_morphemes: bool
    triggered_by: TaskCaller
    overwrite_destination: bool

    def __init_subclass__(cls, **kwargs) -> None:
        # mode is one of ("furigana", "pitch", "audio")
        mode = kwargs.pop("mode")  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[mode] = cls
        cls.mode = mode

    def __new__(cls, mode: str, *args, **kwargs) -> "Profile":
        subclass = cls._subclasses_map[mode]
        return object.__new__(subclass)

    def should_answer_to(self, caller: TaskCaller) -> bool:
        """
        When a task starts, it can refuse to run
        if the caller isn't listed among the callers that the task can be triggered by.
        """
        return caller in self.triggered_by

    def applies_to_note(self, note: AnkiNoteProtocol) -> bool:
        """
        Field names must not be empty or None. The note must have fields with these names.
        """
        return bool((self.source and self.destination) and (self.source in note and self.destination in note))

    @classmethod
    def class_by_mode(cls, mode: str) -> type["Profile"]:
        return cls._subclasses_map[mode]

    @classmethod
    def new(cls, **kwargs):
        return cls(
            mode=cls.mode,
            name="New profile",
            note_type="Japanese",
            split_morphemes=True,
            triggered_by=TaskCaller.all_enabled(),
            overwrite_destination=False,
            **kwargs,
        )

    @classmethod
    def get_default(cls, mode: str):
        return cls.class_by_mode(mode).new()

    @classmethod
    def clone(cls, profile: "Profile"):
        return cls(**dataclasses.asdict(profile))

    def as_config_dict(self) -> dict[str, typing.Union[str, bool]]:
        d = dataclasses.asdict(self)
        d["triggered_by"] = flag_as_comma_separated_list(self.triggered_by)
        return d

    @classmethod
    def from_config_dict(cls, profile_dict: dict):
        # In case new options are added or removed in the future,
        # load default settings first, then overwrite them.
        return cls.get_default(mode=profile_dict["mode"]).replace_from_config_dict(profile_dict)

    def replace_from_config_dict(self, profile_dict):
        if "triggered_by" in profile_dict:
            profile_dict = dict(
                profile_dict,
                # convert from string to the right type.
                triggered_by=flag_from_comma_separated_list(
                    TaskCaller,
                    profile_dict["triggered_by"],
                ),
            )
        return dataclasses.replace(
            self,
            **{key: profile_dict[key] for key in get_common_keys(dataclasses.asdict(self), profile_dict)},
        )


def flag_as_comma_separated_list(flag: enum.Flag):
    assert isinstance(flag, enum.Enum)
    return CFG_WORD_SEP.join(str(item.name) for item in type(flag) if item in flag)
    # note: `item.name for item in flag` won't work on the official Anki build that is still on python 3.9


def flag_from_comma_separated_list(flag_type: enum.EnumMeta, comma_separated_flags: str) -> enum.Flag:
    assert isinstance(comma_separated_flags, str)
    flag: enum.Flag = flag_type(0)
    for string in comma_separated_flags.split(CFG_WORD_SEP):
        if string:
            try:
                flag |= flag_type[string]
            except KeyError:
                pass
    return flag


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
    color_code_pitch: ColorCodePitchFormat

    @classmethod
    def new(cls):
        return super().new(
            source="VocabKanji",
            destination="VocabFurigana",
            color_code_pitch=ColorCodePitchFormat(0),
        )

    def as_config_dict(self) -> dict[str, typing.Union[str, bool]]:
        d = super().as_config_dict()
        d["color_code_pitch"] = flag_as_comma_separated_list(self.color_code_pitch)
        return d

    def replace_from_config_dict(self, profile_dict):
        if "color_code_pitch" in profile_dict:
            profile_dict = dict(
                profile_dict,
                # convert from string to the right type.
                color_code_pitch=flag_from_comma_separated_list(
                    ColorCodePitchFormat,
                    profile_dict["color_code_pitch"],
                ),
            )
        return super().replace_from_config_dict(profile_dict)


@dataclasses.dataclass(frozen=True)
class ProfileAudio(Profile, mode="audio"):
    @classmethod
    def new(cls):
        return super().new(
            source="VocabKanji",
            destination="VocabAudio",
        )
