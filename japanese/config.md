<div style="text-align: center;">
<img style="max-width: 128px; max-height: 128px;" src="https://avatars.githubusercontent.com/u/69172625?s=200&v=4">
</div>

## AJT Japanese &mdash; edit config

Here you can edit the config file.
Doing so can be dangerous.
You must know what you're doing.
Read [the manual](https://tatsumoto.neocities.org/blog/anki-japanese-support.html) before you proceed.
Anki needs to be restarted for changes to be applied.
To restore default settings, click the **"Restore Defaults"** button.

If you have any questions,
ask other users in the [user group](https://tatsumoto.neocities.org/blog/join-our-community.html).

****

### Profiles

Each profile defines
Note Type constraints,
fields to generate data for
and fields where the generated data should be placed.
By default, the add-on matches a note type
if it finds the text "japanese" in the note type name.
Case is ignored.

Default field names match the [TSC](https://ankiweb.net/shared/info/1557722832) note type.

### Furigana

* `skip_numbers`. Whether to add furigana to numbers or not.
* `prefer_literal_pronunciation`.
  The database has readings with the `ー` symbol in place of long vowels.
  Prioritize them, and use single kana to show equivalent sounds, e.g. `を` and `お`.
* `reading_separator`. String used to separate multiple readings of one word. For example, `<br>` or `,`.
* `blocklisted_words`. Furigana won't be added to these words. Comma-separated.
* `mecab_only`. A comma-separated list of words that don't need to be looked up in the database.
* `maximum_results`. Used when database lookups are enabled. Will abort if fetched more results than this number.

### Pitch accent

* `lookup_shortcut`.
  The shortcut to perform pronunciation lookup
  on the selected text ("Tools" > "NHK pitch accent lookup").
* `output_hiragana`.
  Print readings using hiragana instead of katakana.
* `kana_lookups`.
  If failed to find pitch accent for a word,
  make an attempt to look it up using its kana reading.
  Works better if `split_morphemes` is set to `true` in the profile.
* `skip_numbers`. Don't lookup numbers.
* `reading_separator`. String used to separate different readings of one word.
* `word_separator`. String used to separate words.
* `blocklisted_words`. A comma-separated list of words that you don't want to look up.
* `maximum_results`. Abort if fetched more results than this number.

### Context menu

You can enable or disable the following actions:

* `generate_furigana`.
  Paste furigana for selection.
* `to_katakana`.
  Convert selection to katakana.
* `to_hiragana`.
  Convert selection to hiragana.
* `literal_pronunciation`.
  Convert selection to a pronunciation format used in dictionaries (katakana form + certain character conversions).

### Toolbar

Controls additional buttons on the Anki Editor toolbar.

* "Furigana" button lets you generate furigana in the selected field.
* "Clean" button removes furigana in the selected field.
* "Regenerate all" button clears all destination fields and fills them again.

Parameters:

* `enabled`.
  Control whether a button is shown.
* `shortcut`.
  Specify a keyboard shortcut for the button.
* `text`.
  Customize the button's label.

### Audio sources

A list of audio sources used to add audio to cards.

Parameters:

* `enabled`.
  Control whether a source is used.
* `name`.
  User-specified name of the source.
* `url`.
  Path or URL of the audio index.

### Audio settings

* `dictionary_download_timeout`.
  Give up when dictionary downloads take more time than specified.
* `audio_download_timeout`.
  Same but for audio files stored remotely.
* `attempts`.
  Number of times to try to download a file.
* `maximum_results`.
  Limit on the number of files that can be added at once.
* `ignore_inflections`.
  Try to filter out audio files where the word is not in the dictionary form.
* `stop_if_one_source_has_results`.
  If one audio source contains files for a word, skip other audio sources.
* `search_dialog_src_field_name`.
  Remembers last used field name.
* `search_dialog_dest_field_name`.
  Remembers last used field name.
* `tag_separator`.
  String used to separate `[sound:filename.ogg]` tags.

### Other

* `cache_lookups`.
  Size of cache.
  Used internally.
* `insert_scripts_into_templates`.
  The add-on inserts additional JavaScript and CSS code into the card templates
  to enable the display of pitch accent information on mouse hover.
  If you do not require this feature,
  you can disable the script loading
  (and then remove the added scripts from your card templates).

****

If you enjoy this add-on,
please consider [donating](https://tatsumoto.neocities.org/blog/donating-to-tatsumoto.html)
to help me continue to provide you with updates and new features.
Thank you so much for your support and for being a part of our journey!
