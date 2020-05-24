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

from typing import Dict

# pylint: disable=import-error, no-name-in-module
import aqt
from aqt.utils import showWarning, tooltip
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QDialog, QAction
from PyQt5.QtCore import pyqtSignal, QThread

from . import ankisync
from . import import_dialog
from .settings import edit_settings
from . import twimport


class ImportThread(QThread):
    """
    Background thread to export the wiki and parse questions out of it.
    """
    progress_update = pyqtSignal(int, int)

    def __init__(self, conf: dict, wiki_name: str, wiki_conf: Dict[str, str]):
        super().__init__()
        self.conf = conf
        self.wiki_name = wiki_name
        self.wiki_conf = wiki_conf
        self.notes = None
        self.exception = None

    def run(self):
        try:
            self.notes = twimport.find_notes(
                tw_binary=self.conf['tiddlywikiBinary'],
                wiki_path=self.wiki_conf['path'],
                wiki_type=self.wiki_conf['type'],
                wiki_name=self.wiki_name,
                filter_=self.wiki_conf['contentFilter'],
                callback=self.progress_update.emit
            )
            for n in self.notes:
                wiki_url = self.wiki_conf.get('permalink', '')
                if wiki_url:
                    n.set_permalink(wiki_url)
        except Exception as e:
            self.exception = e


class ImportDialog(QDialog):
    """
    Dialog implementing the import from TiddlyWiki.
    """
    def __init__(self, mw):
        QDialog.__init__(self)
        self.form = import_dialog.Ui_Dialog()
        self.form.setupUi(self)
        self.conf = mw.addonManager.getConfig(__name__)
        self.mw = mw

        self.extract_thread = None
        self.notes = []
        self.wikis = [(k, v) for k, v in self.conf['wikis'].items()]
        self.form.wikiProgressBar.setMaximum(len(self.wikis))

    def start_import(self) -> bool:
        """
        Check to make sure import is configured correctly and begin
        extracting data. Return True if started asynchronously, False if
        unable to start.
        """
        # Catch scenario where user tries to sync without configuring and provide
        # a helpful error message.
        if len(self.wikis) == 1 and not self.wikis[0][1]['path'].strip():
            showWarning("You don't appear to have set up any wikis to sync with. "
                        "To do so, choose Tools > Add-ons, select TiddlyRemember, "
                        "and click the Config button.")
            return False

        self.extract()
        return True

    def extract_progress(self, at: int, end: int):
        "Progress callback function for export/parse triggered by progress signal."
        self.form.progressBar.setMaximum(100)
        self.form.text.setText(f"Extracting notes from tiddlers...{at}/{end}")
        if end == 0:
            # Obviously this will be done *real* soon...but don't want an exception!
            self.form.progressBar.setValue(100)
        else:
            self.form.progressBar.setValue(at * 100 / end)

    def extract(self) -> None:
        """
        Extract questions from a TiddlyWiki using Node. When done, proceed to
        sync with Anki.
        """
        wiki_name, wiki_conf = self.wikis.pop()

        self.form.text.setText(f"Exporting tiddlers from {wiki_name}...")
        self.form.progressBar.setMaximum(0)

        self.extract_thread = ImportThread(self.conf, wiki_name, wiki_conf)
        self.extract_thread.finished.connect(self.join_thread)
        self.extract_thread.progress_update.connect(self.extract_progress)
        self.extract_thread.start()

    def join_thread(self) -> None:
        """
        Gather up the results of a completed extract thread, and start the next one
        if appropriate.
        """
        if self.extract_thread.exception:
            self.reject()
            raise self.extract_thread.exception

        if len(self.extract_thread.notes) == 0:
            # This is probably a mistake or misconfiguration. To avoid deleting
            # all the user's existing notes to "sync" the collection, abort now.
            showWarning(
                f"No notes were found in the wiki {self.extract_thread.wiki_name}. "
                f"Please check your add-on configuration. "
                f"Your collection has not been updated.")
            self.reject()
            return

        self.notes.extend(self.extract_thread.notes)

        self.form.wikiProgressBar.setValue(self.form.wikiProgressBar.value() + 1)
        if self.wikis:
            # If there are any more wikis, handle the next one.
            # Eventually, parallelizing this might be nice
            # (might also not improve performance).
            return self.extract()
        else:
            # When all are completed, start the sync with Anki.
            return self.sync()

    def sync(self):
        """
        Compare the notes gathered by the various wiki threads with the notes
        currently in our Anki collection and add, edit, and remove notes as needed
        to get Anki in sync with the TiddlyWiki notes.
        """
        self.form.progressBar.setMaximum(0)
        self.form.text.setText(f"Applying note changes to your collection...")
        userlog = ankisync.sync(self.notes, self.mw, self.conf)

        self.accept()
        self.mw.reset()
        tooltip(userlog)


def open_dialog():
    "Launch the sync dialog."
    dialog = ImportDialog(aqt.mw)
    if dialog.start_import():
        dialog.exec_()


if aqt.mw is not None:
    action = QAction(aqt.mw)
    action.setText("Sync from &TiddlyWiki")
    action.setShortcut(QKeySequence("Shift+Y"))
    aqt.mw.form.menuTools.addAction(action)
    action.triggered.connect(open_dialog)
    aqt.mw.addonManager.setConfigAction(__name__, edit_settings)