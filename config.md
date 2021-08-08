## JaPitch - config

*Anki needs to be restarted for changes to be applied.*

*Default field names match the
[mpvacious cards](https://ankiweb.net/shared/info/1557722832)
note type.*

****

* `noteTypes`.
Constrain the add-on's operation to certain note types.
By default, the add-on considers a note type Japanese
if it finds the text "japanese" in the note type name.
Case is ignored.
* `srcFields`.
Fields to generate readings for.
* `dstFields`.
Fields where the readings should be placed.
* `regenerateReadings`.
When you run "Edit" > "Bulk-add pitch accents"
in the Anki Browser,
readings for each card will be regenerated
even if `dstField` is already filled.
* `pronunciationHiragana`.
Use hiragana instead of katakana for the readings.
* `styles`.
Style mappings. Edit this if you want different colors, etc.
* `useMecab`.
Use Mecab to split a sentence/conjugation when performing lookups.
* `lookupShortcut`.
The shortcut to perform pronunciation lookup
on the selected text ("Tools" > "NHK pitch accent lookup").
* `generateOnNoteFlush`.
Automatically add pronunciations to cards created by AnkiConnect with
[Yomichan](https://foosoft.net/projects/yomichan/).
* `kanaLookups`.
If failed to find pitch accent for a word,
make an attempt to look it up using its kana reading.
Requires `useMecab` set to `true`.
* `skipWords`.
A comma-separated list of words that you don't want to look up.

****

If you enjoy this add-on, please consider supporting my work by
**[pledging your support on Patreon](https://www.patreon.com/bePatron?u=43555128)**.
Thank you so much!
