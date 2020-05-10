##############################################################
# Remember - store questions in a TiddlyWiki
# Copyright 2020 Soren Bjornstad <contact@sorenbjornstad.com>
##############################################################

###############################################################################
# The MIT License:
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################

from typing import Dict, NewType, Set

# pylint: disable=import-error, no-name-in-module
import aqt
from aqt.qt import QAction, QThread
from aqt.utils import getFile, showWarning, askUser, tooltip
from anki.notes import Note
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal

from . import import_dialog
from . import twimport
from .twnote import TwNote

# TiddlyWiki ID
Twid = NewType('Twid', str)


class ImportDialog(QDialog):
    """
    """
    class ImportThread(QThread):
        progress_update = pyqtSignal(int, int)

        def __init__(self, conf):
            super().__init__()
            self.conf = conf

        def run(self):
            self.notes = twimport.find_notes(
                self.conf['tiddlywikiBinary'],
                self.conf['tiddlywikiDirectory'],
                self.conf['filter'],
                self.progress_update.emit)


    def __init__(self, mw):
        self.mw = mw
        QDialog.__init__(self)
        self.form = import_dialog.Ui_Dialog()
        self.form.setupUi(self)
        self.conf = mw.addonManager.getConfig(__name__)
        self.extract()

    def extract_progress(self, at: int, end: int):
        self.form.progressBar.setMaximum(100)
        self.form.progressBar.setValue(at * 100 / end)
        self.form.text.setText(f"Extracting notes from tiddlers...{at}/{end}")

    def extract(self):
        self.extract_thread = self.ImportThread(self.conf)
        self.extract_thread.finished.connect(self.sync)
        self.extract_thread.progress_update.connect(self.extract_progress)
        self.extract_thread.start()

    def sync(self):
        extracted_notes: Set[TwNote] = self.extract_thread.notes
        extracted_twids: Set[Twid] = set(n.id_ for n in extracted_notes)
        extracted_notes_map: Dict[Twid, TwNote] = {n.id_: n for n in extracted_notes}

        anki_notes: Set[Note] = [self.mw.col.getNote(nid)
                                 for nid in self.mw.col.find_notes("note:TWQ")]
        anki_twids: Set[Twid] = set(n.fields[2] for n in anki_notes)
        anki_notes_map: Dict[Twid, Note] = {n.fields[2]: n for n in anki_notes}

        adds = extracted_twids.difference(anki_twids)
        edits = extracted_twids.intersection(anki_twids)
        removes = anki_twids.difference(extracted_twids)

        for note_id in adds:
            tw_note = extracted_notes_map[note_id]
            n = Note(self.mw.col, self.mw.col.models.byName("TWQ"))
            n.model()['did'] = self.mw.col.decks.id("tw")
            n['Question'] = tw_note.question
            n['Answer'] = tw_note.answer
            n['ID'] = tw_note.id_
            n['Reference'] = tw_note.tidref
            self.mw.col.addNote(n)
        print(f"Added {len(adds)} notes.")

        edit_count = 0
        for note_id in edits:
            anki_note = anki_notes_map[note_id]
            tw_note = extracted_notes_map[note_id]
            if not tw_note.fields_equal(anki_note):
                tw_note.update_fields(anki_note)
                anki_note.flush()
                edit_count += 1
        print(f"Updated {edit_count} notes.")

        self.mw.col.remNotes(anki_notes_map[twid].id for twid in removes)
        print(f"Removed {len(removes)} notes.")

        self.mw.reset()
        self.accept()




def open_dialog():
    "Launch the sync dialog."
    dialog = ImportDialog(aqt.mw)
    dialog.exec_()

if aqt.mw is not None:
    action = QAction(aqt.mw)
    action.setText("Sync from &TiddlyWiki")
    aqt.mw.form.menuTools.addAction(action)
    action.triggered.connect(open_dialog)
