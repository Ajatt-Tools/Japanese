# -*- coding: utf-8 -*-

import glob
import io
import pickle
import re
import subprocess
from abc import ABC
from collections import namedtuple, OrderedDict
from gettext import gettext as _
from html.parser import HTMLParser
from typing import Optional

from anki import hooks
from anki.hooks import addHook
from anki.notes import Note
from aqt import mw, gui_hooks
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import isMac, isWin, showInfo, showText

from .helpers import get_notetype

# ************************************************
#                Global Variables                *
# ************************************************

# Paths to the database files and this particular file

this_addon_path = os.path.dirname(os.path.normpath(__file__))
thisfile = os.path.join(this_addon_path, "nhk_pronunciation.py")

db_dir_path = os.path.join(this_addon_path, "accent_dict")
derivative_database = os.path.join(db_dir_path, "nhk_pronunciation.csv")
derivative_pickle = os.path.join(db_dir_path, "nhk_pronunciation.pickle")
accent_database = os.path.join(db_dir_path, "ACCDB_unicode.csv")

# "Class" declaration
AccentEntry = namedtuple('AccentEntry',
                         ['NID', 'ID', 'WAVname', 'K_FLD', 'ACT', 'midashigo', 'nhk', 'kanjiexpr', 'NHKexpr',
                          'numberchars', 'nopronouncepos', 'nasalsoundpos', 'majiri', 'kaisi', 'KWAV', 'midashigo1',
                          'akusentosuu', 'bunshou', 'ac'])

# The main dict used to store all entries
thedict = {}

config = mw.addonManager.getConfig(__name__)


# ************************************************
#                  Helper functions              *
# ************************************************
def katakana_to_hiragana(katakana_expression: str):
    hiragana = u'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ' \
               u'あいうえおかきくけこさしすせそたちつてと' \
               u'なにぬねのはひふへほまみむめもやゆよらりるれろ' \
               u'わをんぁぃぅぇぉゃゅょっ'
    katakana = u'ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ' \
               u'アイウエオカキクケコサシスセソタチツテト' \
               u'ナニヌネノハヒフヘホマミムメモヤユヨラリルレロ' \
               u'ワヲンァィゥェォャュョッ'
    katakana = [ord(char) for char in katakana]
    translate_table = dict(zip(katakana, hiragana))
    return katakana_expression.translate(translate_table)


class HTMLTextExtractor(HTMLParser, ABC):
    def __init__(self):
        if issubclass(self.__class__, object):
            super(HTMLTextExtractor, self).__init__()
        else:
            HTMLParser.__init__(self)
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def get_text(self):
        return ''.join(self.result)


def strip_html_markup(html, recursive=False):
    """
    Strip html markup. If the html contains escaped html markup itself, one
    can use the recursive option to also strip this.
    """
    old_text = None
    new_text = html
    while new_text != old_text:
        old_text = new_text
        s = HTMLTextExtractor()
        s.feed(new_text)
        new_text = s.get_text()

        if not recursive:
            break

    return new_text


def is_supported_notetype(note: Note):
    # Check if this is a supported note type.

    if not config["noteTypes"]:
        # supported note types weren't specified by the user.
        # treat all note types as supported
        return True

    this_notetype = get_notetype(note)['name']
    return any(notetype.lower() in this_notetype.lower() for notetype in config["noteTypes"])


# Ref: https://stackoverflow.com/questions/15033196/using-javascript-to-check-whether-a-string-contains-japanese-characters-includi/15034560#15034560
non_jap_regex = re.compile(u'[^\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f\u4e00-\u9fff\u3400-\u4dbf]+', re.U)
jp_sep_regex = re.compile(u'[・、※【】「」〒◎×〃゜『』《》〜〽。〄〇〈〉〓〔〕〖〗〘 〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿]', re.U)


def split_separators(expr):
    """
    Split text by common separators (like / or ・) into separate words that can
    be looked up.
    """
    expr = strip_html_markup(expr).strip()

    # Replace all typical separators with a space
    expr = re.sub(non_jap_regex, ' ', expr)  # Remove non-Japanese characters
    expr = re.sub(jp_sep_regex, ' ', expr)  # Remove Japanese punctuation
    expr_all = expr.split(' ')

    return expr_all


# ******************************************************************
#                               Mecab                              *
#  Copied from Japanese add-on by Damien Elmes with minor changes. *
# ******************************************************************

class MecabController:

    def __init__(self, mecab_dir_path):
        if mecab_dir_path is None:
            raise ValueError("mecab not found")

        self.mecab_dir_path = os.path.normpath(mecab_dir_path)
        self.mecabCmd = self.munge_for_platform(
            [os.path.join(self.mecab_dir_path, "mecab")] + self.mecab_args() + [
                '-d', self.mecab_dir_path, '-r', os.path.join(self.mecab_dir_path, "mecabrc")])
        self.mecab = None

        if sys.platform == "win32":
            self._si = subprocess.STARTUPINFO()
            try:
                self._si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            except:
                self._si.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        else:
            self._si = None

    @staticmethod
    def munge_for_platform(popen):
        if isWin:
            # popen = [os.path.normpath(x) for x in popen]
            popen[0] += ".exe"
        elif not isMac:
            popen[0] += ".lin"
        return popen

    @staticmethod
    def mecab_args():
        return ['--node-format=%f[6] ', '--eos-format=\n', '--unk-format=%m[] ']

    def setup(self):
        os.environ['DYLD_LIBRARY_PATH'] = self.mecab_dir_path
        os.environ['LD_LIBRARY_PATH'] = self.mecab_dir_path
        if not isWin:
            os.chmod(self.mecabCmd[0], 0o755)

    def ensure_open(self):
        if not self.mecab:
            self.setup()
            try:
                self.mecab = subprocess.Popen(
                    self.mecabCmd, bufsize=-1, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    startupinfo=self._si)
            except OSError as e:
                raise Exception(str(e) + ": Please ensure your Linux system has 64 bit binary support.")

    @staticmethod
    def _escape_text(text):
        # strip characters that trip up kakasi/mecab
        text = text.replace("\n", " ")
        text = text.replace(u'\uff5e', "~")
        text = re.sub("<br( /)?>", "---newline---", text)
        text = strip_html_markup(text, True)
        text = text.replace("---newline---", "<br>")
        return text

    def reading(self, expr):
        self.ensure_open()
        expr = self._escape_text(expr)
        try:
            self.mecab.stdin.write(expr.encode("utf-8", "ignore") + b'\n')
            self.mecab.stdin.flush()
            expr = self.mecab.stdout.readline().rstrip(b'\r\n').decode('utf-8')
        except UnicodeDecodeError as e:
            raise Exception(str(e) + ": Please ensure you have updated to the most recent Japanese Support add-on.")

        return expr


def find_mecab_dir() -> Optional[str]:
    # Check if Mecab is available and/or if the user wants it to be used
    if config['useMecab']:
        # Note that there are no guarantees on the folder name of the Japanese
        # add-on. We therefore have to look recursively in our parent folder.
        mecab_search = glob.glob(
            os.path.join(this_addon_path, os.pardir + os.sep + '**' + os.sep + 'support' + os.sep + 'mecab.exe')
        )
        mecab_exists = len(mecab_search) > 0
        if mecab_exists:
            return os.path.dirname(os.path.normpath(mecab_search[0]))
        else:
            showInfo("NHK-Pronunciation: Mecab use requested, but Japanese add-on with Mecab not found.")


# ************************************************
#           Database generation functions        *
# ************************************************
def format_entry(e):
    """ Format an entry from the data in the original database to something that uses html """
    txt = e.midashigo1
    strlen = len(txt)
    acclen = len(e.ac)
    accent = "0" * (strlen - acclen) + e.ac

    # Get the nasal positions
    nasal = []
    if e.nasalsoundpos:
        positions = e.nasalsoundpos.split('0')
        for p in positions:
            if p:
                nasal.append(int(p))
            if not p:
                # e.g. "20" would result in ['2', '']
                nasal[-1] = nasal[-1] * 10

    # Get the no pronounce positions
    nopron = []
    if e.nopronouncepos:
        positions = e.nopronouncepos.split('0')
        for p in positions:
            if p:
                nopron.append(int(p))
            if not p:
                # e.g. "20" would result in ['2', '']
                nopron[-1] = nopron[-1] * 10

    outstr = ""
    overline = False

    for i in range(strlen):
        a = int(accent[i])
        # Start or end overline when necessary
        if not overline and a > 0:
            outstr = outstr + '<span class="overline">'
            overline = True
        if overline and a == 0:
            outstr = outstr + '</span>'
            overline = False

        if (i + 1) in nopron:
            outstr = outstr + '<span class="nopron">'

        # Add the character stuff
        outstr = outstr + txt[i]

        # Add the pronunciation stuff
        if (i + 1) in nopron:
            outstr = outstr + "</span>"
        if (i + 1) in nasal:
            outstr = outstr + '<span class="nasal">&#176;</span>'

        # If we go down in pitch, add the downfall
        if a == 2:
            outstr = outstr + '</span>&#42780;'
            overline = False

    # Close the overline if it's still open
    if overline:
        outstr = outstr + "</span>"

    return outstr


def build_database():
    """ Build the derived database from the original database """
    tempdict = {}
    entries = []

    file_handle = io.open(accent_database, 'r', encoding="utf-8")
    for line in file_handle:
        line = line.strip()
        substrs = re.findall(r'({.*?,.*?})', line)
        substrs.extend(re.findall(r'(\(.*?,.*?\))', line))
        for s in substrs:
            line = line.replace(s, s.replace(',', ';'))
        entries.append(AccentEntry._make(line.split(",")))
    file_handle.close()

    for e in entries:
        textentry = format_entry(e)

        # A tuple holding both the spelling in katakana, and the katakana with pitch/accent markup
        kanapron = (e.midashigo, textentry)

        # Add expressions for both
        for key in [e.nhk, e.kanjiexpr]:
            if key in tempdict:
                if kanapron not in tempdict[key]:
                    tempdict[key].append(kanapron)
            else:
                tempdict[key] = [kanapron]

    o = io.open(derivative_database, 'w', encoding="utf-8")

    for key in tempdict.keys():
        for kana, pron in tempdict[key]:
            o.write("%s\t%s\t%s\n" % (key, kana, pron))

    o.close()


def read_derivative():
    """ Read the derivative file to memory """
    file_handle = io.open(derivative_database, 'r', encoding="utf-8")

    for line in file_handle:
        key, kana, pron = line.strip().split("\t")
        kanapron = (kana, pron)
        if key in thedict:
            if kanapron not in thedict[key]:
                thedict[key].append(kanapron)
        else:
            thedict[key] = [kanapron]

    file_handle.close()


# ************************************************
#              Lookup Functions                  *
# ************************************************
def inline_style(txt):
    """ Map style classes to their inline version """

    for k, v in config["styles"].items():
        txt = txt.replace(k, v)

    return txt


def get_pronunciations(expr, sanitize=True, recurse=True):
    """
    Search pronuncations for a particular expression

    Returns a dictionary mapping the expression (or sub-expressions contained
    in the expression) to a list of html-styled pronunciations.
    """

    # Sanitize input
    if sanitize:
        expr = strip_html_markup(expr)
        expr = expr.strip()

    ret = OrderedDict()
    if expr in thedict:
        styled_prons = []

        for kana, pron in thedict[expr]:
            inlinepron = inline_style(pron)

            if config["pronunciationHiragana"]:
                inlinepron = katakana_to_hiragana(inlinepron)

            if inlinepron not in styled_prons:
                styled_prons.append(inlinepron)
        ret[expr] = styled_prons
    elif recurse:
        # Try to split the expression in various ways, and check if any of those results
        split_expr = split_separators(expr)

        if len(split_expr) > 1:
            for expr in split_expr:
                ret.update(get_pronunciations(expr, sanitize))

        # Only if lookups were not succesful, we try splitting with Mecab
        if not ret and mecab_reader:
            for sub_expr in mecab_reader.reading(expr).split():
                # Avoid infinite recursion by saying that we should not try
                # Mecab again if we do not find any matches for this sub-
                # expression.
                ret.update(get_pronunciations(sub_expr, sanitize, False))

    return ret


def get_formatted_pronunciations(expr, sep_single="・", sep_multi="、", expr_sep=None, sanitize=True):
    prons = get_pronunciations(expr, sanitize)

    single_merge = OrderedDict()
    for k, v in prons.items():
        single_merge[k] = sep_single.join(v)

    if expr_sep:
        txt = sep_multi.join([u"{}{}{}".format(k, expr_sep, v) for k, v in single_merge.items()])
    else:
        txt = sep_multi.join(single_merge.values())

    return txt


def lookup_pronunciation(expr):
    """ Show the pronunciation when the user does a manual lookup """
    txt = get_formatted_pronunciations(expr, "<br/>\n", "<br/><br/>\n", ":<br/>\n")

    thehtml = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
<HEAD>
<style>
body {
font-size: 30px;
}
</style>
<TITLE>Pronunciations</TITLE>
<meta charset="UTF-8" />
</HEAD>
<BODY>
%s
</BODY>
</HTML>
""" % txt

    showText(thehtml, type="html")


def on_lookup_pronunciation():
    """ Do a lookup on the selection """
    text = mw.web.selectedText()
    text = text.strip()
    if not text:
        showInfo(_("Empty selection."))
        return
    lookup_pronunciation(text)


# ************************************************
#              Interface                         *
# ************************************************

def create_menu() -> QAction:
    """ Add a hotkey and menu entry """
    lookup_action = QAction("NHK pitch accent lookup", mw)
    qconnect(lookup_action.triggered, on_lookup_pronunciation)
    if config["lookupShortcut"]:
        lookup_action.setShortcut(config["lookupShortcut"])
    return lookup_action


def setup_browser_menu(browser: Browser):
    """ Add menu entry to browser window """
    a = QAction("Bulk-add Pronunciations", browser)
    a.triggered.connect(lambda: on_regenerate(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)


def on_regenerate(browser):
    regenerate_pronunciations(browser.selectedNotes())


def get_src_dst_fields(fields):
    """ Set source and destination fieldnames """
    src = None
    src_idx = None
    dst = None
    dst_idx = None

    for index, field in enumerate(config["srcFields"]):
        if field in fields:
            src = field
            src_idx = index
            break

    for index, field in enumerate(config["dstFields"]):
        if field in fields:
            dst = field
            dst_idx = index
            break

    return src, src_idx, dst, dst_idx


def add_pronunciation_on_focus_lost(flag, note: Note, f_inx):
    if not is_supported_notetype(note):
        return flag

    fields = note.keys()

    src, src_idx, dst, dst_idx = get_src_dst_fields(fields)

    if not src or not dst:
        return flag

    # dst field already filled?
    if note[dst]:
        return flag

    # event coming from src field?
    if f_inx != src_idx:
        return flag

    # grab source text
    src_txt = mw.col.media.strip(note[src])
    if not src_txt:
        return flag

    # update field
    try:
        note[dst] = get_formatted_pronunciations(src_txt)
    except Exception:
        raise
    return True


def regenerate_pronunciations(nids):
    mw.checkpoint("Bulk-add Pronunciations")
    mw.progress.start()
    for nid in nids:
        note = mw.col.getNote(nid)

        if not is_supported_notetype(note):
            continue

        src, src_idx, dst, dst_idx = get_src_dst_fields(note)

        if src is None or dst is None:
            continue

        if note[dst] and not config["regenerateReadings"]:
            # already contains data, skip
            continue

        src_txt = mw.col.media.strip(note[src])
        if not src_txt.strip():
            continue

        note[dst] = get_formatted_pronunciations(src_txt)

        note.flush()
    mw.progress.finish()
    mw.reset()


def on_note_will_flush(note):
    if mw.app.activeWindow() is not None:
        # only accept calls when add cards dialog or anki browser are not open.
        # otherwise this function conflicts with add_pronunciation_focusLost which is called on 'editFocusLost'
        return note

    if not (is_supported_notetype(note) is True and config["generateOnNoteFlush"] is True):
        return note

    src_field, src_idx, dst_field, dst_idx = get_src_dst_fields(note)

    if src_field is None or dst_field is None:
        return note

    if config["regenerateReadings"] is False and note[dst_field] and note[dst_field] != "No pitch accent data":
        # already contains data, skip
        # but yomichan adds `No pitch accent data` to the field when there's no pitch available.
        return note

    src_txt = mw.col.media.strip(note[src_field])
    if not src_txt.strip():
        return note

    note[dst_field] = get_formatted_pronunciations(src_txt)

    return note


# ************************************************
#                   Main                         *
# ************************************************

if not os.path.isdir(db_dir_path):
    raise IOError("Accent database folder is missing!")

# First check that either the original database, or the derivative text file are present:
if not os.path.exists(derivative_database) and not os.path.exists(accent_database):
    raise IOError("Could not locate the original base or the derivative database!")

# Generate the derivative database if it does not exist yet
if (os.path.exists(accent_database) and not os.path.exists(derivative_database)) or (
        os.path.exists(accent_database) and os.stat(thisfile).st_mtime > os.stat(derivative_database).st_mtime):
    build_database()

# If a pickle exists of the derivative file, use that. Otherwise, read from the derivative file and generate a pickle.
if (os.path.exists(derivative_pickle) and
        os.stat(derivative_pickle).st_mtime > os.stat(derivative_database).st_mtime):
    f = io.open(derivative_pickle, 'rb')
    thedict = pickle.load(f)
    f.close()
else:
    read_derivative()
    f = io.open(derivative_pickle, 'wb')
    pickle.dump(thedict, f, pickle.HIGHEST_PROTOCOL)
    f.close()

try:
    mecab_reader = MecabController(find_mecab_dir())
except ValueError:
    mecab_reader = None

# Create the manual look-up menu entry
mw.form.menuTools.addAction(create_menu())

# Generate when editing a note
addHook('editFocusLost', add_pronunciation_on_focus_lost)

# Bulk add
gui_hooks.browser_menus_did_init.append(setup_browser_menu)

# Generate when AnkiConnect adds a new note
hooks.note_will_flush.append(on_note_will_flush)
