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

from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal
import aqt
from aqt.qt import QAction, QThread
from aqt.utils import getFile, showWarning, askUser, tooltip
from anki.notes import Note

from . import import_dialog
from . import twimport


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
        self.import_()

    def update_progress(self, at: int, end: int):
        self.form.progressBar.setMaximum(100)
        self.form.progressBar.setValue(at * 100 / end)
        self.form.text.setText(f"Extracting notes from tiddlers...{at}/{end}")

    def import_(self):
        self.import_thread = self.ImportThread(self.conf)
        self.import_thread.finished.connect(self.accept)
        self.import_thread.progress_update.connect(self.update_progress)
        self.import_thread.start()

    def accept(self):
        showWarning(str(self.import_thread.notes))
        super().accept()




def open_dialog():
    "Launch the add-poem dialog."
    dialog = ImportDialog(aqt.mw)
    dialog.exec_()

action = QAction(aqt.mw)
action.setText("Import from &TiddlyWiki...")
aqt.mw.form.menuTools.addAction(action)
action.triggered.connect(open_dialog)
