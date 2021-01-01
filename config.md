## JaPitch - config

*Anki needs to be restarted for changes to be applied.*

*Default field names are set to match the
[mpvacious cards](https://ankiweb.net/shared/info/1557722832)
note type.*

****

* `noteTypes` - By default, the add-on considers a note type Japanese
if it finds the text "japanese" in the note type name. Case is ignored.

* `srcFields` - Fields to generate the reading for.

* `dstFields` - Fields where the reading should be placed.

* `regenerateReadings` - If a card is shown, should readings for the card be regenerated
if the dstField is already filled? Note that these regenerated readings are *not stored, only shown*.

* `pronunciationHiragana` - Use hiragana instead of katakana for the readings.

* `styles` - Style mappings. Edit this if you want different colors, etc.

* `useMecab` - Whether or not to try and use Mecab
to split a sentence/conjugation when performing lookups.
The [Japanese add-on](https://ankiweb.net/shared/info/3918629684)
is required for this to work.

* `lookupShortcut` - The shortcut to perform pronunciation lookup
on the selected text (Tools > Lookup > ...NHK pitch accent).

* `generateOnNoteFlush` - Automatically add pronunciations to cards created by AnkiConnect with Yomichan.
