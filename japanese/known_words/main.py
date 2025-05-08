import re
import csv
import os
import datetime
import logging

from typing import Set, List, Dict, Optional, Any, Tuple

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, Qt,
    QComboBox, QSpinBox, QFormLayout, QFileDialog, QLineEdit,
    QRadioButton, QButtonGroup, QCheckBox, QTextEdit, QGroupBox,
    QApplication, QWidget, QTabWidget,
    QFrame,
)
from aqt.utils import showInfo, QProgressDialog, tooltip
from anki.utils import strip_html_media


# --- Configuration Keys ---
CONFIG_KEY_LAST_CSV_PATH = "knownWordsCsvLastPath"
CONFIG_KEY_NOTE_TYPE_FILTER_STRING = "knownWordsCsvNoteTypeFilterString"
CONFIG_KEY_LAST_FIELD = "knownWordsCsvLastField"
CONFIG_KEY_LAST_INTERVAL = "knownWordsCsvLastInterval"
CONFIG_KEY_LAST_OPERATION_MODE = "knownWordsCsvLastOpMode"
CONFIG_KEY_LEMMATIZE = "knownWordsCsvLemmatize"
CONFIG_KEY_FILTER_BY_DICT = "knownWordsCsvFilterByDict"
CONFIG_KEY_LAST_DICT_PATH = "knownWordsCsvLastDictPath"
CONFIG_KEY_AUTO_TIMESTAMP_FILENAME = "knownWordsCsvAutoTimestamp"
CONFIG_KEY_CUSTOM_STOPWORDS = "knownWordsCsvCustomStopwords"
CONFIG_KEY_CUSTOM_STOPWORDS_MODE = "knownWordsCsvCustomStopwordsMode"

# --- String Constants ---
STOPWORDS_MODE_SUPPLEMENT = "supplement"
STOPWORDS_MODE_REPLACE = "replace"

CSV_COLUMN_WORD = "Word"
CSV_COLUMN_SOURCE = "Source"

ANKI_SOURCE_TAG = "anki"

OP_MODE_UPDATE_EXISTING = "update_existing"
OP_MODE_SAVE_AS_NEW = "save_as_new"

DEFAULT_SAVE_FILENAME = "known_words.csv"
DEFAULT_NOTE_TYPE_FILTER_STRING = "japanese"
DEFAULT_MATURE_INTERVAL = 21

_SINGLE_DBL_QUOTE = '"'
_ESCAPED_DBL_QUOTE = '""'


# --- Logging Setup ---
log = logging.getLogger(__name__)


# --- MeCab Dependency Handling ---
try:
    from ..mecab_controller import MecabController
    from ..mecab_controller.basic_types import PartOfSpeech
    MECAB_AVAILABLE = True
except ImportError:
    MECAB_AVAILABLE = False
    log.warning("MecabController or basic_types not found. Lemmatization will be disabled.")

    class MecabController: # type: ignore
        def translate(self, text: str) -> list:
            return []

    class _DummyPosValue:
        def __init__(self, value: str):
            self.value = value
        def __str__(self) -> str:
            return self.value
        def __repr__(self) -> str:
            return f"_DummyPosValue('{self.value}')"

    class DummyPartOfSpeech: # type: ignore
        particle = _DummyPosValue("DUMMY_POS_particle")
        bound_auxiliary = _DummyPosValue("DUMMY_POS_bound_auxiliary")
        symbol = _DummyPosValue("DUMMY_POS_symbol")
        filler = _DummyPosValue("DUMMY_POS_filler")
        interjection = _DummyPosValue("DUMMY_POS_interjection")
        prefix = _DummyPosValue("DUMMY_POS_prefix")
        verb = _DummyPosValue("DUMMY_POS_verb")
        noun = _DummyPosValue("DUMMY_POS_noun")
        i_adjective = _DummyPosValue("DUMMY_POS_i_adjective")
        adverb = _DummyPosValue("DUMMY_POS_adverb")
        conjunction = _DummyPosValue("DUMMY_POS_conjunction")
        adnominal_adjective = _DummyPosValue("DUMMY_POS_adnominal_adjective")
        unknown = _DummyPosValue("DUMMY_POS_unknown")
        other = _DummyPosValue("DUMMY_POS_other")

        def __getattr__(self, name: str) -> _DummyPosValue:
            log.debug(f"DummyPartOfSpeech.__getattr__ called for unknown POS: {name}")
            return _DummyPosValue(f"DUMMY_POS_unknown_{name.lower()}")

    PartOfSpeech = DummyPartOfSpeech()

def _load_dictionary_file(filepath: str) -> Set[str]:
    dictionary_set: Set[str] = set()
    if not filepath or not os.path.exists(filepath):
        return dictionary_set

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word:
                    dictionary_set.add(word)
    except (OSError, UnicodeDecodeError) as e: # MODIFIED: IOError to OSError
        log.error(f"Error reading dictionary file '{os.path.basename(filepath)}': {e}", exc_info=True)
        showInfo(f"Error reading dictionary file '{os.path.basename(filepath)}':\n{e}")
    except Exception as e:
        log.error(f"Unexpected error reading dictionary file '{os.path.basename(filepath)}': {e}", exc_info=True)
        showInfo(f"An unexpected error occurred while reading dictionary file '{os.path.basename(filepath)}':\n{e}")
    return dictionary_set


class MeCabProcessor:
    STATUS_UNINITIALIZED = "UNINITIALIZED"
    STATUS_INITIALIZED = "INITIALIZED"
    STATUS_FAILED = "FAILED"

    DEFAULT_POS_TO_SKIP_NAMES: List[str] = [
        "particle", "bound_auxiliary", "symbol", "filler",
        "interjection", "prefix",
    ]
    SINGLE_KANA_REGEX = re.compile(r'^[\u3040-\u309F\u30A0-\u30FF]$')
    FULLWIDTH_ALPHANUM_REGEX = re.compile(r'^[Ａ-Ｚａ-ｚ０-９]+$')
    COUNTER_REGEX = re.compile(r'^\d+[つ個台本枚匹頭羽人日円年々ヵヶ箇カ]$')
    UNWANTED_SYMBOLS: Set[str] = {"「", "」", "、", "。", "？", "！", "：", "；", "（", "）", "【", "】", "『", "』"}

    def __init__(self, custom_stopwords_str: str = "", stopwords_mode: str = STOPWORDS_MODE_SUPPLEMENT):
        self.mecab_controller: Optional[MecabController] = None
        self._pos_to_skip: Set[str] = set()
        self.pos_init_status: str = self.STATUS_UNINITIALIZED
        self.combined_lemma_stop_list: Set[str] = set()

        self._configure_stopwords(custom_stopwords_str, stopwords_mode)

        if MECAB_AVAILABLE:
            try:
                self.mecab_controller = MecabController()
                self._initialize_pos_skip_set()
            except Exception as e:
                log.error(f"Failed to initialize MeCabController: {e}", exc_info=True)
                self.pos_init_status = self.STATUS_FAILED
                self.mecab_controller = None
        else:
            log.info("MeCab is not available. Lemmatization features will be disabled.")
            self.pos_init_status = self.STATUS_FAILED

    def _configure_stopwords(self, custom_stopwords_str: str, stopwords_mode: str) -> None:
        base_stopwords = {"ある", "いる", "する", "なる", "思う"}
        custom_stopwords = {word.strip() for word in custom_stopwords_str.splitlines() if word.strip()}

        if stopwords_mode == STOPWORDS_MODE_REPLACE:
            self.combined_lemma_stop_list = custom_stopwords
        else:
            self.combined_lemma_stop_list = base_stopwords.union(custom_stopwords)

    def _initialize_pos_skip_set(self) -> None:
        if self.pos_init_status != self.STATUS_UNINITIALIZED:
            return

        temp_pos_set: Set[str] = set()
        try:
            for pos_name in self.DEFAULT_POS_TO_SKIP_NAMES:
                if hasattr(PartOfSpeech, pos_name):
                    pos_attr = getattr(PartOfSpeech, pos_name)
                    if hasattr(pos_attr, 'value'):
                        temp_pos_set.add(pos_attr.value)
                    else:
                        log.warning(f"PartOfSpeech attribute '{pos_name}' (type: {type(pos_attr)}) lacks a '.value' attribute. Skipping.")
                else:
                    log.warning(f"PartOfSpeech enum (real or dummy) does not have attribute '{pos_name}'. Skipping for POS filter.")

            self._pos_to_skip = temp_pos_set
            if not self._pos_to_skip and self.DEFAULT_POS_TO_SKIP_NAMES:
                log.warning("POS skip set is empty after initialization, though default names were provided. Check PartOfSpeech definitions.")
            self.pos_init_status = self.STATUS_INITIALIZED
            log.debug(f"POS skip set initialized: {self._pos_to_skip}")

        except Exception as e:
            log.error(f"Error initializing Part-of-Speech skip set: {e}", exc_info=True)
            self.pos_init_status = self.STATUS_FAILED

    def get_lemmas(self, text: str) -> Set[str]:
        lemmas: Set[str] = set()

        if not self.mecab_controller or self.pos_init_status == self.STATUS_FAILED:
            log.debug("MeCab controller not available or POS init failed. Skipping lemmatization.")
            return lemmas

        if self.pos_init_status == self.STATUS_UNINITIALIZED:
            log.warning("get_lemmas called while POS uninitialized. Attempting re-initialization.")
            self._initialize_pos_skip_set()
            if self.pos_init_status != self.STATUS_INITIALIZED:
                log.error("Re-initialization of POS failed. Cannot get lemmas.")
                return lemmas

        try:
            tokens_raw = self.mecab_controller.translate(text)
            if not isinstance(tokens_raw, (list, tuple)):
                 log.warning(f"MecabController.translate returned an unexpected type: {type(tokens_raw)}. Expected list or tuple.")
                 return lemmas

            for token_idx, token in enumerate(tokens_raw):
                surface_word = getattr(token, 'word', '')
                lemma_cand = getattr(token, 'headword', '')
                raw_token_pos = getattr(token, 'part_of_speech', None)
                token_pos_val: Optional[str] = None

                if raw_token_pos is not None:
                    if hasattr(raw_token_pos, 'value'):
                        token_pos_val = raw_token_pos.value
                    else:
                        log.warning(f"Token POS object {raw_token_pos} (type: {type(raw_token_pos)}) at index {token_idx} lacks .value. Using str().")
                        token_pos_val = str(raw_token_pos)
                
                if token_pos_val is not None and token_pos_val in self._pos_to_skip:
                    continue

                lemma_to_process = (lemma_cand or surface_word).strip()
                if not lemma_to_process: continue
                if lemma_to_process in self.combined_lemma_stop_list: continue
                if len(lemma_to_process) == 1 and self.SINGLE_KANA_REGEX.fullmatch(lemma_to_process): continue
                if self.FULLWIDTH_ALPHANUM_REGEX.fullmatch(lemma_to_process): continue
                if lemma_to_process.isnumeric(): continue
                if self.COUNTER_REGEX.fullmatch(lemma_to_process): continue
                if lemma_to_process in self.UNWANTED_SYMBOLS: continue

                lemmas.add(lemma_to_process)
        except Exception as e:
            log.error(f"Error during lemmatization of text snippet '{text[:50]}...': {e}", exc_info=True)
        return lemmas

    def test_mecab_and_pos(self) -> bool:
        if not self.mecab_controller:
            log.warning("MeCab test: Controller not available.")
            return False
        if self.pos_init_status == self.STATUS_FAILED:
            log.warning("MeCab test: POS initialization failed.")
            return False
        if self.pos_init_status == self.STATUS_UNINITIALIZED:
            log.info("MeCab test: POS uninitialized, attempting to initialize.")
            self._initialize_pos_skip_set()
            if self.pos_init_status != self.STATUS_INITIALIZED:
                log.warning("MeCab test: POS re-initialization failed.")
                return False

        test_passed = True
        try:
            lemmas_verb = self.get_lemmas("食べる")
            if not lemmas_verb or "食べる" not in lemmas_verb:
                log.warning(f"MeCab self-test (1): Failed to lemmatize '食べる' as expected. Got: {lemmas_verb}")
        except Exception as e:
            log.error(f"MeCab self-test (1): Error during lemmatization of '食べる': {e}", exc_info=True)
            return False

        particle_pos_value = None
        if hasattr(PartOfSpeech, 'particle') and hasattr(getattr(PartOfSpeech, 'particle'), 'value'):
            particle_pos_value = getattr(PartOfSpeech, 'particle').value
        
        if self.pos_init_status == self.STATUS_INITIALIZED and particle_pos_value in self._pos_to_skip:
            lemmas_particle = self.get_lemmas("猫が可愛い")
            if "が" in lemmas_particle:
                log.warning(f"MeCab self-test (2): Particle 'が' was not filtered. Got: {lemmas_particle}. Skipped POS: {self._pos_to_skip}")
        
        test_stopword = "する"
        if test_stopword in self.combined_lemma_stop_list:
            lemmas_stopword = self.get_lemmas(f"勉強{test_stopword}")
            if test_stopword in lemmas_stopword:
                log.warning(f"MeCab self-test (3): Stopword '{test_stopword}' was not filtered. Got: {lemmas_stopword}")
                test_passed = False
        
        if test_passed:
            log.info("MeCab self-test passed (basic functionality and critical filtering). Warnings may indicate sub-optimal configuration or MeCab variability.")
        else:
            log.warning("MeCab self-test indicated potential issues. Review warnings.")
        return test_passed

    def update_stopwords(self, custom_stopwords_str: str, mode: str) -> None:
        self._configure_stopwords(custom_stopwords_str, mode)


class KnownWordsProcessor:
    def __init__(self, col: Any, mecab_processor: Optional[MeCabProcessor], progress_parent: Optional[QWidget] = None):
        self.col = col
        self.mecab_processor = mecab_processor
        self.progress_parent = progress_parent

    def read_csv_data(self, filepath: str) -> Dict[str, Set[str]]: # Renamed from read_existing_csv
        data: Dict[str, Set[str]] = {}
        if not filepath or not os.path.exists(filepath):
            if filepath:
                showInfo(f"Specified CSV file not found: {os.path.basename(filepath)}")
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                except StopIteration:
                    showInfo(f"CSV file '{os.path.basename(filepath)}' is empty.")
                    return {}
                
                if not header or len(header) < 2 or \
                   header[0].lower().strip() != CSV_COLUMN_WORD.lower() or \
                   header[1].lower().strip() != CSV_COLUMN_SOURCE.lower():
                    showInfo(f"CSV file '{os.path.basename(filepath)}' has an invalid header. "
                             f"Expected '{CSV_COLUMN_WORD}' and '{CSV_COLUMN_SOURCE}'.")
                    return {}

                for row_idx, row in enumerate(reader, 1):
                    if not row or len(row) < 1 or not row[0].strip():
                        continue
                    word = row[0].strip()
                    sources_str = (row[1].strip() if len(row) > 1 and row[1] else "")
                    data[word] = set(s.strip() for s in sources_str.split(',') if s.strip())
        except (OSError, csv.Error) as e: # Changed IOError to OSError for consistency
            log.error(f"Error reading CSV file '{os.path.basename(filepath)}': {e}", exc_info=True)
            showInfo(f"Error reading CSV file '{os.path.basename(filepath)}':\n{e}")
            return {}
        except Exception as e:
            log.error(f"Unexpected error reading CSV file '{os.path.basename(filepath)}': {e}", exc_info=True)
            showInfo(f"An unexpected error occurred while reading CSV file '{os.path.basename(filepath)}':\n{e}")
            return {}
        return data

    def get_anki_data(self, query: str, sentence_field_name: str,
                      mature_interval: int, use_lemmatization: bool) -> Set[str]: # Renamed from _get_anki_data
        anki_items: Set[str] = set()
        if not query:
            log.info("get_anki_data: Query is empty, returning no items.")
            return anki_items

        try:
            note_ids: List[int] = self.col.find_notes(query)
        except Exception as e:
            log.error(f"Error finding notes with query '{query}': {e}", exc_info=True)
            showInfo(f"Error searching Anki notes (check query syntax in logs):\n{e}")
            return anki_items

        if not note_ids:
            log.info(f"get_anki_data: No notes found for query '{query}'.")
            return anki_items

        # Use self.progress_parent if available for the QProgressDialog
        progress_dialog_parent = self.progress_parent if self.progress_parent else mw
        progress = QProgressDialog(
            f"Scanning Anki notes (field: '{sentence_field_name}')...", 
            "Cancel", 0, len(note_ids), 
            progress_dialog_parent # Parent appropriately
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)

        processed_count = 0
        for idx, nid in enumerate(note_ids):
            if idx % 50 == 0:
                progress.setValue(idx)
                QApplication.processEvents()

            if progress.wasCanceled():
                showInfo("Operation cancelled by user.")
                return set()

            note = self.col.get_note(nid)
            if not note:
                log.warning(f"Could not retrieve note with nid {nid}. Skipping.")
                continue
            if sentence_field_name not in note:
                log.debug(f"Field '{sentence_field_name}' not in note {nid} (type: {note.note_type()['name'] if note.note_type() else 'Unknown'}). Skipping.")
                continue
            
            is_mature_enough = False
            if mature_interval > 0:
                cards = note.cards()
                if not cards:
                    is_mature_enough = False
                else:
                    for card in cards:
                        if card.ivl >= mature_interval:
                            is_mature_enough = True
                            break
                if not is_mature_enough:
                    continue
            
            text_raw = note[sentence_field_name]
            if not text_raw or not text_raw.strip():
                continue
            text_cleaned = strip_html_media(text_raw)

            if use_lemmatization and self.mecab_processor and \
               self.mecab_processor.pos_init_status == MeCabProcessor.STATUS_INITIALIZED: # Stricter check
                try:
                    lemmas_from_field = self.mecab_processor.get_lemmas(text_cleaned)
                    anki_items.update(lemmas_from_field)
                except Exception as e:
                    log.error(f"Error lemmatizing field content from note {nid}: {e}", exc_info=True)
            else:
                temp_val = re.sub(r'\s*[（(].*?[）)]\s*|\s*\[.*?\]\s*|[\uff08\uff09\u3010\u3011\u300c\u300d\u300e\u300f]', '', text_cleaned).strip()
                words_from_field = re.split(r'[\s\uff0c\u3001\uff0e\u3002\uff1f\uff01\uff1b\uff1a?!”;:]+', temp_val)
                anki_items.update(word for word in words_from_field if word)
            processed_count +=1

        progress.setValue(len(note_ids))
        log.info(f"Processed {processed_count}/{len(note_ids)} notes. Extracted {len(anki_items)} unique items from Anki.")
        return anki_items

    def merge_data(self, existing_csv_data: Dict[str, Set[str]],
                   anki_items: Set[str]) -> Tuple[Dict[str, Set[str]], Dict[str, int]]: # Renamed from _merge_csv_data
        merged_data = {k: set(v) for k, v in existing_csv_data.items()}
        stats = {
            "anki_source_removed_not_in_anki": 0,
            "word_deleted_no_sources_left": 0,
            "new_word_from_anki_added": 0,
            "anki_source_added_to_existing_word": 0
        }

        for word in list(merged_data.keys()):
            sources = merged_data[word]
            if ANKI_SOURCE_TAG in sources and word not in anki_items:
                sources.remove(ANKI_SOURCE_TAG)
                stats["anki_source_removed_not_in_anki"] += 1
                if not sources:
                    del merged_data[word]
                    stats["word_deleted_no_sources_left"] += 1
            elif not sources:
                del merged_data[word]

        for item in anki_items:
            if item in merged_data:
                if ANKI_SOURCE_TAG not in merged_data[item]:
                    merged_data[item].add(ANKI_SOURCE_TAG)
                    stats["anki_source_added_to_existing_word"] +=1
            else:
                merged_data[item] = {ANKI_SOURCE_TAG}
                stats["new_word_from_anki_added"] += 1
        return merged_data, stats

    def write_csv_data(self, output_path: str, data_to_write: Dict[str, Set[str]]) -> bool: # Renamed from _write_csv_data
        output_rows: List[List[str]] = [[CSV_COLUMN_WORD, CSV_COLUMN_SOURCE]]
        for word, sources in sorted(data_to_write.items()):
            if sources:
                output_rows.append([word, ",".join(sorted(list(sources)))])

        if len(output_rows) <= 1:
            showInfo("No data to save (either no words found or all words had no sources).")
            return False

        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                csv_writer = csv.writer(f)
                csv_writer.writerows(output_rows)
            return True
        except OSError as e: # Changed IOError to OSError
            log.error(f"OSError writing CSV file to '{os.path.basename(output_path)}': {e}", exc_info=True)
            showInfo(f"Error writing CSV file to '{os.path.basename(output_path)}':\n{e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error writing CSV to '{os.path.basename(output_path)}': {e}", exc_info=True)
            showInfo(f"An unexpected error occurred while writing CSV to '{os.path.basename(output_path)}':\n{e}")
            return False


class ExportVocabCsvDialog(QDialog):
    # Class constants for UI related default values / preferences
    DEFAULT_FIELD_SUGGESTION = "SentKanji"
    PREFERRED_FIELDS_ORDER = [DEFAULT_FIELD_SUGGESTION, "VocabKanji", "Expression", "Sentence"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Known Words")
        self.setMinimumWidth(800)

        self.mecab_processor: Optional[MeCabProcessor] = None
        if MECAB_AVAILABLE:
            try:
                addon_config = mw.addonManager.getConfig(__name__.split('.')[0]) if mw else {}
                _initial_custom_stopwords = addon_config.get(CONFIG_KEY_CUSTOM_STOPWORDS, "")
                _initial_stopwords_mode = addon_config.get(CONFIG_KEY_CUSTOM_STOPWORDS_MODE, STOPWORDS_MODE_SUPPLEMENT)
                self.mecab_processor = MeCabProcessor(
                    custom_stopwords_str=_initial_custom_stopwords,
                    stopwords_mode=_initial_stopwords_mode
                )
            except Exception as e:
                log.error(f"Failed to initialize MeCabProcessor for dialog: {e}", exc_info=True)
                self.mecab_processor = None
                showInfo("Error initializing MeCab processor. Lemmatization may be unavailable. Check logs.")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        tab_widget = QTabWidget()

        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout(tab1_widget)
        tab1_layout.setSpacing(12)
        tab1_layout.setContentsMargins(8, 8, 8, 8)

        anki_source_groupbox = self._setup_anki_source_group()
        csv_dictionary_groupbox = self._setup_csv_dictionary_group()

        tab1_layout.addWidget(anki_source_groupbox)
        tab1_layout.addWidget(csv_dictionary_groupbox)
        tab1_layout.addStretch(1)
        tab1_widget.setLayout(tab1_layout)
        tab_widget.addTab(tab1_widget, "Core Settings")

        tab2_widget = QWidget()
        tab2_layout = QVBoxLayout(tab2_widget)
        tab2_layout.setSpacing(12)
        tab2_layout.setContentsMargins(8, 8, 8, 8)

        lemmatization_groupbox = self._setup_lemmatization_group()
        mecab_test_groupbox = self._setup_mecab_test_group()

        tab2_layout.addWidget(lemmatization_groupbox)
        tab2_layout.addWidget(mecab_test_groupbox)
        tab2_layout.addStretch(1)
        tab2_widget.setLayout(tab2_layout)
        tab_widget.addTab(tab2_widget, "Lemmatization and Tools")

        buttons_layout = self._setup_buttons_layout()

        main_layout.addWidget(tab_widget)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

        self.load_settings()
        self.update_operation_mode_state()
        self._update_mecab_processor_stopwords()
        self.update_dict_filter_state()

    def _setup_anki_source_group(self) -> QGroupBox:
        groupbox = QGroupBox("Anki Data Source")
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(10, 10, 10, 10)

        self.note_type_filter_edit = QLineEdit()
        self.note_type_filter_edit.setPlaceholderText("e.g., japanese, basic")
        form_layout.addRow("Process Note Types Containing:", self.note_type_filter_edit)

        self.field_combo = QComboBox()
        self.populate_field_combo()
        form_layout.addRow("Sentence/Word Field:", self.field_combo)

        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(0)
        self.interval_spinbox.setMaximum(9999)
        self.interval_spinbox.setValue(DEFAULT_MATURE_INTERVAL)
        self.interval_spinbox.setSuffix(" days")
        form_layout.addRow("Mature Interval (>=):", self.interval_spinbox)

        groupbox.setLayout(form_layout)
        return groupbox

    def _setup_csv_dictionary_group(self) -> QGroupBox:
        groupbox = QGroupBox("CSV File and Dictionary Settings")
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(10, 10, 10, 10)

        csv_path_options_layout = QHBoxLayout()
        csv_path_options_layout.setSpacing(6)

        self.csv_path_edit = QLineEdit()
        self.csv_path_edit.setPlaceholderText("(Optional) Select CSV to read/update")
        csv_path_options_layout.addWidget(self.csv_path_edit, 1)

        self.auto_timestamp_checkbox = QCheckBox("Timestamp new filenames")
        self.auto_timestamp_checkbox.setToolTip("Append _YYYY-MM-DD_HHMMSS to new filenames.")
        csv_path_options_layout.addWidget(self.auto_timestamp_checkbox)

        self.select_csv_button = QPushButton("Browse...")
        self.select_csv_button.clicked.connect(self.select_existing_csv)
        csv_path_options_layout.addWidget(self.select_csv_button)
        form_layout.addRow("CSV File:", csv_path_options_layout)
        self.csv_path_edit.textChanged.connect(self.update_operation_mode_state)

        self.operation_group = QButtonGroup(self)
        self.radio_update_existing = QRadioButton("Update selected CSV directly")
        self.radio_save_as_new = QRadioButton("Save results to a new/different CSV file")
        self.operation_group.addButton(self.radio_update_existing)
        self.operation_group.addButton(self.radio_save_as_new)
        operation_layout = QVBoxLayout()
        operation_layout.setContentsMargins(0,0,0,0)
        operation_layout.setSpacing(4)
        operation_layout.addWidget(self.radio_update_existing)
        operation_layout.addWidget(self.radio_save_as_new)
        self.radio_save_as_new.setChecked(True)
        form_layout.addRow("CSV Operation:", operation_layout)

        line_separator = QFrame()
        line_separator.setFrameShape(QFrame.Shape.HLine)
        line_separator.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow(line_separator)


        self.filter_by_dict_checkbox = QCheckBox("Filter extracted words against a dictionary file")
        self.filter_by_dict_checkbox.setToolTip("Only include words/lemmas from Anki if they also exist in the specified dictionary file.")
        self.filter_by_dict_checkbox.stateChanged.connect(self.update_dict_filter_state)
        form_layout.addRow("", self.filter_by_dict_checkbox)

        self.dict_path_edit = QLineEdit()
        self.dict_path_edit.setPlaceholderText("Path to dictionary (one word per line, .txt, .raw)")
        self.select_dict_button = QPushButton("Browse...")
        self.select_dict_button.clicked.connect(self.select_dictionary_file)

        self.dict_path_layout_container = QHBoxLayout()
        self.dict_path_layout_container.setSpacing(6)
        self.dict_path_layout_container.addWidget(self.dict_path_edit, 1)
        self.dict_path_layout_container.addWidget(self.select_dict_button)

        self.dict_path_row_label = QLabel("Dictionary File:")
        form_layout.addRow(self.dict_path_row_label, self.dict_path_layout_container)

        groupbox.setLayout(form_layout)
        return groupbox

    def _setup_lemmatization_group(self) -> QGroupBox:
        groupbox = QGroupBox("Lemmatization Settings")
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(10, 10, 10, 10)

        self.lemmatize_checkbox = QCheckBox("Extract lemmas using MeCab")
        if self.is_lemmatization_module_available:
            self.lemmatize_checkbox.setChecked(True)
            self.lemmatize_checkbox.setToolTip("Process Anki field to extract dictionary form of words using MeCab.")
        else:
            self.lemmatize_checkbox.setChecked(False)
            self.lemmatize_checkbox.setEnabled(False)
            tooltip_msg = "MeCab components not found or Part-of-Speech initialization failed. Lemmatization disabled."
            self.lemmatize_checkbox.setToolTip(tooltip_msg)
        form_layout.addRow(self.lemmatize_checkbox)

        self.custom_stopwords_edit = QTextEdit()
        self.custom_stopwords_edit.setPlaceholderText("Enter custom stopwords (one per line).\nThese supplement or replace built-in stopwords.")
        self.custom_stopwords_edit.setMinimumHeight(80)
        form_layout.addRow("Custom Stopwords:", self.custom_stopwords_edit)

        self.stopwords_mode_group = QButtonGroup(self)
        self.stopwords_supplement_radio = QRadioButton("Supplement built-in stopwords")
        self.stopwords_replace_radio = QRadioButton("Replace built-in stopwords")
        self.stopwords_mode_group.addButton(self.stopwords_supplement_radio)
        self.stopwords_mode_group.addButton(self.stopwords_replace_radio)
        self.stopwords_supplement_radio.setChecked(True)
        stopwords_mode_layout = QHBoxLayout()
        stopwords_mode_layout.setSpacing(10)
        stopwords_mode_layout.addWidget(self.stopwords_supplement_radio)
        stopwords_mode_layout.addWidget(self.stopwords_replace_radio)
        stopwords_mode_layout.addStretch()
        self.stopwords_supplement_radio.clicked.connect(self._on_custom_stopwords_changed)
        self.stopwords_replace_radio.clicked.connect(self._on_custom_stopwords_changed)
        self.custom_stopwords_edit.textChanged.connect(self._on_custom_stopwords_changed)
        form_layout.addRow("Stopwords Mode:", stopwords_mode_layout)

        groupbox.setLayout(form_layout)
        groupbox.setEnabled(self.is_lemmatization_module_available)
        return groupbox

    def _setup_mecab_test_group(self) -> QGroupBox:
        groupbox = QGroupBox("MeCab Test Tool")
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(10, 10, 10, 10)

        self.mecab_test_input_edit = QLineEdit()
        self.mecab_test_input_edit.setPlaceholderText("Enter Japanese text here...")
        self.mecab_test_run_button = QPushButton("Test Lemmatization")
        self.mecab_test_run_button.clicked.connect(self.on_mecab_test_run_clicked)

        input_button_layout = QHBoxLayout()
        input_button_layout.setSpacing(6)
        input_button_layout.addWidget(self.mecab_test_input_edit, 1)
        input_button_layout.addWidget(self.mecab_test_run_button)
        form_layout.addRow("Test Text:", input_button_layout)

        self.mecab_test_output_display = QTextEdit()
        self.mecab_test_output_display.setReadOnly(True)
        self.mecab_test_output_display.setPlaceholderText("Lemmatized output will appear here.")
        self.mecab_test_output_display.setMinimumHeight(100)
        form_layout.addRow("Output:", self.mecab_test_output_display)

        groupbox.setLayout(form_layout)
        groupbox.setEnabled(self.is_lemmatization_module_available)
        if not self.is_lemmatization_module_available:
            groupbox.setToolTip("MeCab is not available or not initialized correctly.")
        return groupbox

    def _setup_buttons_layout(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        self.process_button = QPushButton("Process and Save CSV")
        self.process_button.clicked.connect(self.on_process_button_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        layout.addStretch()
        layout.addWidget(self.process_button)
        layout.addWidget(self.cancel_button)
        return layout

    @property
    def is_lemmatization_module_available(self) -> bool:
        return (MECAB_AVAILABLE and
                self.mecab_processor is not None and
                self.mecab_processor.pos_init_status != MeCabProcessor.STATUS_FAILED)

    @property
    def is_lemmatization_fully_functional(self) -> bool:
        return (MECAB_AVAILABLE and
                self.mecab_processor is not None and
                self.mecab_processor.pos_init_status == MeCabProcessor.STATUS_INITIALIZED)

    def _get_start_directory(self, current_path_text: str) -> str:
        if current_path_text:
            current_path_abs = os.path.abspath(current_path_text)
            if os.path.isfile(current_path_abs):
                return os.path.dirname(current_path_abs)
            if os.path.isdir(current_path_abs):
                 return current_path_abs
        if mw and mw.pm and hasattr(mw.pm, 'profileFolder') and mw.pm.profileFolder():
            return mw.pm.profileFolder()
        return os.path.expanduser("~")

    def update_dict_filter_state(self) -> None:
        is_checked = self.filter_by_dict_checkbox.isChecked()
        self.dict_path_row_label.setVisible(is_checked)
        self.dict_path_edit.setVisible(is_checked)
        self.select_dict_button.setVisible(is_checked)
        self.dict_path_edit.setEnabled(is_checked)
        self.select_dict_button.setEnabled(is_checked)

    def select_dictionary_file(self) -> None:
        start_dir = self._get_start_directory(self.dict_path_edit.text())
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Dictionary File", start_dir, "Text Files (*.txt *.raw);;All Files (*)"
        )
        if path:
            self.dict_path_edit.setText(path)

    def populate_field_combo(self) -> None:
        if not mw or not mw.col:
            log.warning("Cannot populate field combo: Anki collection not available.")
            self.field_combo.addItem("Error: Anki collection not available")
            self.field_combo.setEnabled(False)
            return

        all_fields: Set[str] = set()
        try:
            for model in mw.col.models.all():
                for field_dict in model['flds']:
                    all_fields.add(field_dict['name'])
        except Exception as e:
            log.error(f"Error loading fields from Anki models: {e}", exc_info=True)
            self.field_combo.addItem("Error loading fields")
            self.field_combo.setEnabled(False)
            return

        if not all_fields:
            self.field_combo.addItem("No fields found")
            self.field_combo.setEnabled(False)
            return

        sorted_fields = sorted(list(all_fields))
        
        current_selection = ""
        for pf in self.PREFERRED_FIELDS_ORDER:
            if pf in all_fields:
                current_selection = pf
                break
        
        if not current_selection and self.DEFAULT_FIELD_SUGGESTION in all_fields:
            current_selection = self.DEFAULT_FIELD_SUGGESTION
        
        if not current_selection and sorted_fields:
            current_selection = sorted_fields[0]

        self.field_combo.clear()
        self.field_combo.addItems(sorted_fields)
        
        if current_selection:
            idx = self.field_combo.findText(current_selection)
            if idx != -1:
                self.field_combo.setCurrentIndex(idx)
            elif self.field_combo.count() > 0:
                 self.field_combo.setCurrentIndex(0)
        elif self.field_combo.count() > 0:
             self.field_combo.setCurrentIndex(0)


    def update_operation_mode_state(self) -> None:
        has_input_path = bool(self.csv_path_edit.text().strip())
        self.radio_update_existing.setEnabled(has_input_path)
        if not has_input_path and self.radio_update_existing.isChecked():
            self.radio_save_as_new.setChecked(True)

    def _update_mecab_processor_stopwords(self) -> None:
        if self.mecab_processor:
            custom_stopwords = self.custom_stopwords_edit.toPlainText()
            mode = STOPWORDS_MODE_REPLACE if self.stopwords_replace_radio.isChecked() else STOPWORDS_MODE_SUPPLEMENT
            try:
                self.mecab_processor.update_stopwords(custom_stopwords, mode)
            except Exception as e:
                log.error(f"Error updating MeCab processor stopwords: {e}", exc_info=True)

    def _on_custom_stopwords_changed(self) -> None:
        self._update_mecab_processor_stopwords()

    def load_settings(self) -> None:
        if not mw:
            log.warning("Cannot load settings: Anki environment (mw) not available.")
            return

        addon_package = __name__.split('.')[0]
        config = mw.addonManager.getConfig(addon_package) or {}

        self.csv_path_edit.setText(config.get(CONFIG_KEY_LAST_CSV_PATH, ""))
        note_type_filter = config.get(CONFIG_KEY_NOTE_TYPE_FILTER_STRING, DEFAULT_NOTE_TYPE_FILTER_STRING)
        self.note_type_filter_edit.setText(note_type_filter)
        last_field = config.get(CONFIG_KEY_LAST_FIELD, self.DEFAULT_FIELD_SUGGESTION)
        idx_field = self.field_combo.findText(last_field)
        if idx_field != -1:
            self.field_combo.setCurrentIndex(idx_field)
        elif self.field_combo.count() > 0:
            if not self.field_combo.currentText():
                self.field_combo.setCurrentIndex(0)

        self.interval_spinbox.setValue(config.get(CONFIG_KEY_LAST_INTERVAL, DEFAULT_MATURE_INTERVAL))
        last_op_mode = config.get(CONFIG_KEY_LAST_OPERATION_MODE, OP_MODE_SAVE_AS_NEW)
        if last_op_mode == OP_MODE_UPDATE_EXISTING and self.radio_update_existing.isEnabled():
            self.radio_update_existing.setChecked(True)
        else:
            self.radio_save_as_new.setChecked(True)

        if self.is_lemmatization_module_available:
            self.lemmatize_checkbox.setChecked(config.get(CONFIG_KEY_LEMMATIZE, True))
            self.custom_stopwords_edit.setPlainText(config.get(CONFIG_KEY_CUSTOM_STOPWORDS, ""))
            stopwords_mode = config.get(CONFIG_KEY_CUSTOM_STOPWORDS_MODE, STOPWORDS_MODE_SUPPLEMENT)
            if stopwords_mode == STOPWORDS_MODE_REPLACE:
                self.stopwords_replace_radio.setChecked(True)
            else:
                self.stopwords_supplement_radio.setChecked(True)
        
        self._update_mecab_processor_stopwords()

        self.auto_timestamp_checkbox.setChecked(config.get(CONFIG_KEY_AUTO_TIMESTAMP_FILENAME, False))
        self.filter_by_dict_checkbox.setChecked(config.get(CONFIG_KEY_FILTER_BY_DICT, False))
        self.dict_path_edit.setText(config.get(CONFIG_KEY_LAST_DICT_PATH, ""))
        self.update_dict_filter_state()

    def save_settings(self) -> None:
        if not mw:
            log.warning("Cannot save settings: Anki environment (mw) not available.")
            return

        addon_package = __name__.split('.')[0]
        config = mw.addonManager.getConfig(addon_package) or {}

        config[CONFIG_KEY_LAST_CSV_PATH] = self.csv_path_edit.text()
        config[CONFIG_KEY_NOTE_TYPE_FILTER_STRING] = self.note_type_filter_edit.text()
        config[CONFIG_KEY_LAST_FIELD] = self.field_combo.currentText()
        config[CONFIG_KEY_LAST_INTERVAL] = self.interval_spinbox.value()
        config[CONFIG_KEY_LAST_OPERATION_MODE] = OP_MODE_UPDATE_EXISTING if self.radio_update_existing.isChecked() else OP_MODE_SAVE_AS_NEW

        if self.is_lemmatization_module_available:
            config[CONFIG_KEY_LEMMATIZE] = self.lemmatize_checkbox.isChecked()
            config[CONFIG_KEY_CUSTOM_STOPWORDS] = self.custom_stopwords_edit.toPlainText()
            config[CONFIG_KEY_CUSTOM_STOPWORDS_MODE] = STOPWORDS_MODE_REPLACE if self.stopwords_replace_radio.isChecked() else STOPWORDS_MODE_SUPPLEMENT
        else:
            config.pop(CONFIG_KEY_LEMMATIZE, None)
            config.pop(CONFIG_KEY_CUSTOM_STOPWORDS, None)
            config.pop(CONFIG_KEY_CUSTOM_STOPWORDS_MODE, None)

        config[CONFIG_KEY_AUTO_TIMESTAMP_FILENAME] = self.auto_timestamp_checkbox.isChecked()
        config[CONFIG_KEY_FILTER_BY_DICT] = self.filter_by_dict_checkbox.isChecked()
        config[CONFIG_KEY_LAST_DICT_PATH] = self.dict_path_edit.text()

        try:
            mw.addonManager.writeConfig(addon_package, config)
        except Exception as e:
            log.error(f"Error writing addon config: {e}", exc_info=True)
            showInfo(f"Could not save settings: {e}")

    def select_existing_csv(self) -> None:
        start_dir = self._get_start_directory(self.csv_path_edit.text())
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", start_dir, "CSV Files (*.csv);;All Files (*)")
        if path:
            self.csv_path_edit.setText(path)
    
    # Method _determine_output_path remains in ExportVocabCsvDialog as it directly uses UI elements
    # for QFileDialog and radio button states.
    def _determine_output_path(self) -> Optional[str]:
        input_csv_path = self.csv_path_edit.text().strip()
        output_path: Optional[str] = None

        if self.radio_update_existing.isChecked():
            if not input_csv_path:
                showInfo("Cannot update: No input CSV file specified.")
                return None
            if not os.path.exists(input_csv_path) or not os.path.isfile(input_csv_path):
                showInfo(f"Cannot update: Specified input CSV file does not exist or is not a file:\n{input_csv_path}")
                return None
            output_path = input_csv_path
        elif self.radio_save_as_new.isChecked():
            start_dir = self._get_start_directory(input_csv_path)
            suggested_filename_base = DEFAULT_SAVE_FILENAME
            if input_csv_path:
                if os.path.isfile(input_csv_path):
                    suggested_filename_base = os.path.basename(input_csv_path)
                elif os.path.isdir(input_csv_path):
                    start_dir = input_csv_path
            
            initial_file_path_suggestion = os.path.join(start_dir, suggested_filename_base)
            filter_string_for_dialog = "CSV Files (*.csv);;All Files (*)"
            raw_path, _ = QFileDialog.getSaveFileName(
                self, "Save Known Words CSV", initial_file_path_suggestion, filter_string_for_dialog
            ) # QFileDialog needs a parent, `self` (the dialog) is appropriate
            
            if not raw_path:
                return None

            name, ext = os.path.splitext(raw_path)
            if ext.lower() != ".csv":
                raw_path = name + ".csv"

            if self.auto_timestamp_checkbox.isChecked():
                name_no_ext, current_ext = os.path.splitext(raw_path)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
                output_path = f"{name_no_ext}_{timestamp}{current_ext}"
            else:
                output_path = raw_path
        
        if output_path and os.path.splitext(output_path)[1].lower() != ".csv":
            output_path = os.path.splitext(output_path)[0] + ".csv"
            log.warning(f"Output path extension corrected to .csv: {output_path}")
        return output_path

    def on_process_button_clicked(self) -> None:
        if not mw or not mw.col:
            log.critical("Anki collection (mw.col) is not available. Cannot proceed.")
            showInfo("Critical error: Anki collection (mw.col) is not available. Cannot proceed.")
            return

        # Instantiate the processor, passing `self` as progress_parent
        processor = KnownWordsProcessor(mw.col, self.mecab_processor, progress_parent=self)

        note_type_filter_text = self.note_type_filter_edit.text().strip()
        if not note_type_filter_text:
            showInfo("Please enter a filter string for note type names (e.g., 'japanese'). Cannot be empty.")
            return
        
        normalized_filter = note_type_filter_text.lower()
        try:
            all_note_type_infos = mw.col.models.all_names_and_ids()
        except Exception as e:
            log.error(f"Error fetching note type names and IDs: {e}", exc_info=True)
            showInfo(f"Could not retrieve note type information from Anki: {e}")
            return

        if not all_note_type_infos:
            showInfo("No note types found in your Anki collection.")
            return

        matching_model_names = []
        for nt_info in all_note_type_infos:
            if normalized_filter in nt_info.name.lower():
                matching_model_names.append(nt_info.name)
        
        if not matching_model_names:
            showInfo(f"No note types found with names containing: '{note_type_filter_text}'.")
            return

        note_type_queries = [f'note:"{name.replace(_SINGLE_DBL_QUOTE, _ESCAPED_DBL_QUOTE)}"' for name in matching_model_names]
        anki_query = f"({' OR '.join(note_type_queries)})"
        log.info(f"Constructed Anki query: {anki_query}")

        input_csv_path = self.csv_path_edit.text().strip()
        selected_field_name = self.field_combo.currentText()
        mature_interval = self.interval_spinbox.value()
        # Check for lemmatization fully functional (stricter) before enabling
        use_lemmatization = (self.is_lemmatization_fully_functional and 
                             self.lemmatize_checkbox.isChecked())
        
        use_dictionary_filter = self.filter_by_dict_checkbox.isChecked()
        dictionary_path = self.dict_path_edit.text().strip()
        dictionary_set: Set[str] = set()

        if not selected_field_name or selected_field_name in ["No fields found", "Error loading fields", "Error: Anki collection not available"]:
            showInfo("Please select a valid Anki Field to process.")
            return

        if use_dictionary_filter:
            if not dictionary_path:
                showInfo("Dictionary filtering is enabled, but no dictionary file path is specified.")
                return
            if not os.path.exists(dictionary_path):
                showInfo(f"Dictionary file not found at: {dictionary_path}")
                return
            dictionary_set = _load_dictionary_file(dictionary_path) # _load_dictionary_file is a module-level function
            if not dictionary_set and os.path.exists(dictionary_path):
                showInfo(f"The dictionary file '{os.path.basename(dictionary_path)}' was found but is empty or failed to load. "
                         "Filtering against an empty dictionary will result in no words from Anki being included.")

        if use_lemmatization and self.mecab_processor: # mecab_processor must exist for use_lemmatization to be true
            self._update_mecab_processor_stopwords() # Dialog method updates its mecab_processor instance
            if not self.mecab_processor.test_mecab_and_pos():
                tooltip("Warning: MeCab self-test failed. Lemmatization results may be inaccurate. Check add-on logs for details.", period=7000, parent=self)

        existing_csv_data: Dict[str, Set[str]] = {}
        if input_csv_path:
            if self.radio_update_existing.isChecked() and not os.path.exists(input_csv_path):
                showInfo(f"Update operation selected, but the CSV file does not exist: {input_csv_path}")
                return
            existing_csv_data = processor.read_csv_data(input_csv_path) # Use processor instance

        anki_items_raw = processor.get_anki_data(
            anki_query, selected_field_name,
            mature_interval, use_lemmatization
        ) 

        anki_items_final: Set[str]
        filtered_out_by_dict_count = 0
        if use_dictionary_filter:
            original_count = len(anki_items_raw)
            anki_items_final = {item for item in anki_items_raw if item in dictionary_set}
            filtered_out_by_dict_count = original_count - len(anki_items_final)
            if not anki_items_final and original_count > 0:
                showInfo(f"No Anki items matched the words in the provided dictionary. "
                         f"{original_count} items were initially extracted from Anki; all {filtered_out_by_dict_count} were filtered out by the dictionary.")
        else:
            anki_items_final = anki_items_raw

        if not anki_items_final and not existing_csv_data:
            message = "No Anki items to process (none found matching criteria"
            if use_dictionary_filter and anki_items_raw:
                 message += ", or all filtered out by dictionary"
            message += ") and no existing CSV data to merge/update. Nothing to save."
            showInfo(message)
            return

        merged_data, merge_stats = processor.merge_data(existing_csv_data, anki_items_final) # Use processor instance

        output_path = self._determine_output_path() # This dialog method remains as it needs UI state
        if not output_path:
            tooltip("Save operation cancelled or output path could not be determined.", parent=self)
            return

        if processor.write_csv_data(output_path, merged_data): # Use processor instance
            num_words_saved = len(merged_data)
            stats_summary_parts = [
                f"New from Anki: {merge_stats['new_word_from_anki_added']}",
                f"Anki source added: {merge_stats['anki_source_added_to_existing_word']}",
                f"Anki source removed (no longer in Anki selection): {merge_stats['anki_source_removed_not_in_anki']}",
                f"Words deleted (no sources left): {merge_stats['word_deleted_no_sources_left']}"
            ]
            if use_dictionary_filter:
                stats_summary_parts.append(f"Filtered out by dictionary: {filtered_out_by_dict_count}")
            stats_summary = ". ".join(stats_summary_parts) + "."
            
            parent_widget_for_final_info = self if self.isVisible() else mw 
            showInfo(f"Successfully saved {num_words_saved} words to:\n{os.path.basename(output_path)}\n\nSummary:\n{stats_summary}",
                     parent=parent_widget_for_final_info)

            if output_path.lower() != self.csv_path_edit.text().strip().lower():
                self.csv_path_edit.setText(output_path)
                self.update_operation_mode_state()

            self.save_settings()
            self.accept()
    
    def on_mecab_test_run_clicked(self) -> None:
        test_text = self.mecab_test_input_edit.text().strip()
        self.mecab_test_output_display.clear()

        if not self.mecab_processor:
            msg = "MeCab processor is not available (MeCab components might be missing or failed to load). Lemmatization features disabled."
            self.mecab_test_output_display.setText(msg)
            log.warning("Mecab test: mecab_processor is None.")
            return

        if not self.is_lemmatization_fully_functional:
            msg = "MeCab is not fully functional for testing. "
            if not MECAB_AVAILABLE: msg += "MeCab components are not installed. "
            elif self.mecab_processor.pos_init_status == MeCabProcessor.STATUS_FAILED: msg += "Part-of-Speech initialization failed. "
            elif self.mecab_processor.pos_init_status == MeCabProcessor.STATUS_UNINITIALIZED:
                msg += "Part-of-Speech uninitialized. Attempting re-initialization..."
                log.info("MeCab test: POS uninitialized, attempting re-init.")
                self.mecab_processor._initialize_pos_skip_set()
                if self.is_lemmatization_fully_functional:
                    msg += "\nRe-initialization successful. Try testing again."
                else:
                    msg += "\nRe-initialization failed. Check logs for details."
            else:
                msg += "Current status: " + self.mecab_processor.pos_init_status + ". Check logs."
            
            self.mecab_test_output_display.setText(msg)
            log.warning(f"Mecab test: Not fully functional. Status: {self.mecab_processor.pos_init_status}")
            return

        if not test_text:
            self.mecab_test_output_display.setText("Please enter some Japanese text to test.")
            return

        try:
            self._update_mecab_processor_stopwords()
            lemmas = self.mecab_processor.get_lemmas(test_text)
            if lemmas:
                self.mecab_test_output_display.setText("\n".join(sorted(list(lemmas))))
            else:
                self.mecab_test_output_display.setText("No lemmas extracted. Input might be empty after processing, "
                                                       "all tokens might be stopwords, or filtered by Part-of-Speech rules.")
        except Exception as e:
            log.error(f"An error occurred during MeCab lemmatization test: {e}", exc_info=True)
            self.mecab_test_output_display.setText(f"An error occurred during lemmatization test:\n{e}")

def show_export_vocab_csv_dialog():
    if not mw:
        log.error("Cannot show dialog: Anki environment (mw) not available.")
        showInfo("Anki environment (mw) not available. Cannot open dialog.")
        return
    dialog = ExportVocabCsvDialog(mw)
    dialog.exec()
