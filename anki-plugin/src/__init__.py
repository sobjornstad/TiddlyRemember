##############################################################
# TiddlyRemember - store Anki notes in a NodeJS TiddlyWiki
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

from . import ankisync
from . import import_dialog
from . import twimport
from .twnote import TwNote
from .util import Twid

class ImportDialog(QDialog):
    """
    Dialog implementing the import from TiddlyWiki.
    """
    class ImportThread(QThread):
        """
        Background thread to export the wiki and parse questions out of it.
        """
        progress_update = pyqtSignal(int, int)

        def __init__(self, conf):
            super().__init__()
            self.conf = conf

        def run(self):
            self.notes = twimport.find_notes(
                tw_binary=self.conf['tiddlywikiBinary'],
                wiki_path=self.conf['wiki']['path'],
                wiki_type=self.conf['wiki']['type'],
                filter_=self.conf['wiki']['contentFilter'],
                callback=self.progress_update.emit
            )
            for n in self.notes:
                wiki_url = self.conf['wiki'].get('permalink', None)
                if wiki_url is not None:
                    n.set_permalink(wiki_url)


    def __init__(self, mw):
        self.mw = mw
        QDialog.__init__(self)
        self.form = import_dialog.Ui_Dialog()
        self.form.setupUi(self)
        self.conf = mw.addonManager.getConfig(__name__)
        self.extract()

    def extract_progress(self, at: int, end: int):
        "Progress callback function for export/parse triggered by progress signal."
        self.form.progressBar.setMaximum(100)
        self.form.progressBar.setValue(at * 100 / end)
        self.form.text.setText(f"Extracting notes from tiddlers...{at}/{end}")

    def extract(self):
        """
        Extract questions from a TiddlyWiki using Node. When done, proceed to
        sync with Anki.
        """
        self.extract_thread = self.ImportThread(self.conf)
        self.extract_thread.finished.connect(self.sync)
        self.extract_thread.progress_update.connect(self.extract_progress)
        self.extract_thread.start()

    def sync(self):
        """
        After an extract() run, the notes extracted are available from
        self.extract_thread. Compare these notes with the notes currently in
        our Anki collection and add, edit, and remove notes as needed to get
        Anki in sync with the TiddlyWiki notes.
        """
        self.form.progressBar.setMaximum(0)
        self.form.text.setText(f"Applying note changes to your collection...")

        userlog = ankisync.sync(self.extract_thread.notes, self.mw, self.conf)

        self.accept()
        self.mw.reset()
        tooltip(userlog)


def pluralize(sg: str, n: int, pl: str = None):
    if n == 1:
        return sg
    else:
        if pl is None:
            pl = sg + 's'
        return pl


def open_dialog():
    "Launch the sync dialog."
    dialog = ImportDialog(aqt.mw)
    dialog.exec_()


if aqt.mw is not None:
    action = QAction(aqt.mw)
    action.setText("Sync from &TiddlyWiki")
    aqt.mw.form.menuTools.addAction(action)
    action.triggered.connect(open_dialog)
