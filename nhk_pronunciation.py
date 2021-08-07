# -*- coding: utf-8 -*-

import glob
import subprocess
from collections import OrderedDict
from gettext import gettext as _
from typing import Optional

from anki import hooks
from anki.hooks import addHook
from aqt import gui_hooks
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import isMac, isWin, showInfo, showText

from .database import init as database_init
from .helpers import *


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

        os.environ['DYLD_LIBRARY_PATH'] = self.mecab_dir_path
        os.environ['LD_LIBRARY_PATH'] = self.mecab_dir_path
        print("Japitch cmd", self.mecabCmd)

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
        return ['--node-format=%f[6] ', '--unk-format=%m ', '--eos-format=\n']

    def ensure_open(self):
        if not self.mecab:
            try:
                self.mecab = subprocess.Popen(
                    self.mecabCmd, bufsize=-1, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    startupinfo=self._si)
            except OSError as e:
                raise Exception(str(e) + ": Please ensure your Linux system has 64 bit binary support.")

    def reading(self, expr):
        self.ensure_open()
        expr = escape_text(expr)
        try:
            self.mecab.stdin.write(expr.encode("utf-8", "ignore") + b'\n')
            self.mecab.stdin.flush()
            expr = self.mecab.stdout.readline().rstrip(b'\r\n').decode('utf-8')
        except UnicodeDecodeError as e:
            raise Exception(str(e) + ": Please ensure you have updated to the most recent Japanese Support add-on.")
        except BrokenPipeError:
            self.mecab = None

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
#              Lookup Functions                  *
# ************************************************

def convert_to_inline_style(txt: str) -> str:
    """ Map style classes to their inline version """

    for k, v in config["styles"].items():
        txt = txt.replace(k, v)

    return txt


def get_pronunciations(expr: str, sanitize=True, recurse=True):
    """
    Search pronuncations for a particular expression

    Returns a dictionary mapping the expression (or sub-expressions contained
    in the expression) to a list of html-styled pronunciations.
    """

    # Sanitize input
    if sanitize:
        expr = htmlToTextLine(expr)

    ret = OrderedDict()
    if expr in acc_dict:
        styled_prons = []

        for kana, pron in acc_dict[expr]:
            inline_pron = convert_to_inline_style(pron)

            if config["pronunciationHiragana"]:
                inline_pron = katakana_to_hiragana(inline_pron)

            if inline_pron not in styled_prons:
                styled_prons.append(inline_pron)
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


def get_formatted_pronunciations(expr: str, sep_single="・", sep_multi="、", expr_sep=None, sanitize=True):
    prons = get_pronunciations(expr, sanitize)

    single_merge = OrderedDict()
    for k, v in prons.items():
        single_merge[k] = sep_single.join(v)

    if expr_sep:
        txt = sep_multi.join([u"{}{}{}".format(k, expr_sep, v) for k, v in single_merge.items()])
    else:
        txt = sep_multi.join(single_merge.values())

    return txt



# ************************************************
#              Interface                         *
# ************************************************




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

try:
    mecab_reader = MecabController(find_mecab_dir())
except ValueError:
    mecab_reader = None

acc_dict = database_init()


def init():

    # Generate when editing a note
    addHook('editFocusLost', add_pronunciation_on_focus_lost)
    # the new hook often fails:
    # gui_hooks.editor_did_unfocus_field.append(add_pronunciation_on_focus_lost)

    # Bulk add
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)

    # Generate when AnkiConnect adds a new note
    hooks.note_will_flush.append(on_note_will_flush)
