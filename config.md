## AJT Pitch Accent - config

*Anki needs to be restarted for changes to be applied.*

*Default field names match the
[mpvacious cards](https://ankiweb.net/shared/info/1557722832)
note type.*

****

* `profiles`.
Each profile defines
Note Type constraints,
fields to generate pitch accents for
and fields where the pitch accents should be placed.
By default, the add-on matches a note type
if it finds the text "japanese" in the note type name.
Case is ignored.
* `regenerate_readings`.
When you run "Edit" > "Bulk-add pitch accents"
in the Anki Browser,
readings for each card will be regenerated
even if `dstField` is already filled.
* `use_hiragana`.
Use hiragana instead of katakana for the readings.
* `styles`.
Style mappings. Edit this if you want different colors, etc.
* `use_mecab`.
Use Mecab to split a sentence/conjugation when performing lookups.
* `lookup_shortcut`.
The shortcut to perform pronunciation lookup
on the selected text ("Tools" > "NHK pitch accent lookup").
* `generate_on_note_add`.
Automatically add pronunciations to cards created by AnkiConnect with
[Yomichan](https://foosoft.net/projects/yomichan/).
* `kana_lookups`.
If failed to find pitch accent for a word,
make an attempt to look it up using its kana reading.
Requires `use_mecab` set to `true`.
* `skip_words`.
A comma-separated list of words that you don't want to look up.

****

If you enjoy this add-on, please consider supporting my work by
**[pledging your support on Patreon](https://www.patreon.com/bePatron?u=43555128)**.
Thank you so much!
