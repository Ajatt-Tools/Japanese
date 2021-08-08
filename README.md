# AJT Pitch Accent

This add-on allows you to look up the Japanese pitch accent of a particular expression.
For this to work,
you have to add a `VocabPitchPattern` field to your notes,
and lookups will be done on the `VocabKanji` field.
You can change both these field names (or add more source fields) in the config.

## Installation
Install from [AnkiWeb](https://ankiweb.net/shared/info/1225470483),
or manually with `git`:

```
git clone 'https://github.com/Ajatt-Tools/PitchAccent.git' ~/.local/share/Anki2/addons21/pitch_accent
```

## Configuration
To configure the add-on, open the Anki Add-on Menu
via `Tools > Add-ons` and select `AJT Pitch Accent`.
Then click the `Config` button on the right-side of the screen.

## Usage

When adding cards, the pronunciation is automatically looked-up
and added to its field (similar to the Japanese support add-on).

A lookup on a selection. Select the expression you would like to look up,
and go to "Tools" > "NHK pitch accent lookup".

By opening the Anki Browser, you can mass-generate pitch accents in bulk.
To do this, select some notes first,
and then choose "Edit" > "Bulk-add pitch accents" from the menu.
By default, the "bulk-add" feature will not overwrite the `VocabPitchPattern` field if its already filled,
but you can change this by setting "regenerateReadings" to `True` in the config.

## Pitch accent, what is that?

For more information on the Japanese pitch accent,
I would like to refer you to http://en.wikipedia.org/wiki/Japanese_pitch_accent.

In short, the following notations can be found:

* **Overline:** Indicates "High" pitch (see "Binary pitch" in Wikipedia article).
* **Downfall arrow:** usually means stressing the mora/syllable before.
* **Red circle mark:** Nasal pronunciation、e.g. `げ` would be a nasal `け`.
* **Blue color:** barely pronounced at all.

For example, a blue `ヒ` would be closer to `h` than `hi`.
Likewise, a blue `ク` would be more like a `k` than `ku`.

I can't speak for someone else, but for me,
just knowing about the pitch accent and how it might affect the meaning
has helped me a great deal.
There are some tricky words like はし and じどう,
where different pronunciations have wildly varying meanings.
Aside from that, knowing about these rules might help you
avoid speaking with a distinct foreign accent.

## Acknowledgements

This add-on is a completely remastered version of
[Japanese Pronunciation / Pitch Accent](https://ankiweb.net/shared/info/932119536).

The changes include:

* Significantly refactored 99% of the codebase.
* Completely removed annoying features.
* Preconfigured the default config file for use with
[mpvacious cards](https://ankiweb.net/shared/info/1557722832).
* Added kana lookups.
* Fixed a great number of bugs.
* Bundled [Mecab controller](https://github.com/Ajatt-Tools/mecab_controller) with the add-on.
