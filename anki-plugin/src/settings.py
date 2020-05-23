import copy
import subprocess

import aqt
from aqt.qt import QAction, QThread, QKeySequence
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QComboBox, QApplication
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import pyqtSignal, Qt
from aqt.utils import getFile, showWarning, showInfo, showCritical, askUser

from . import settings_dialog


class SettingsDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.mw = aqt.mw
        self.form = settings_dialog.Ui_Dialog()
        self.form.setupUi(self)
        self.deckChooser = aqt.deckchooser.DeckChooser(self.mw, self.form.deckWidget,
                                                       label=False)

        self.form.okButton.clicked.connect(self.accept)
        self.form.cancelButton.clicked.connect(self.reject)
        self.form.helpButton.clicked.connect(self.get_help)
        self.form.addWikiButton.clicked.connect(self.add_wiki)
        self.form.deleteWikiButton.clicked.connect(self.delete_wiki)
        self.form.browseButton.clicked.connect(self.browse_for_wiki)
        self.form.testExecutableButton.clicked.connect(self.test_executable)
        self.form.type_.currentTextChanged.connect(self.type_changed)
        self.form.wikiList.currentRowChanged.connect(self.wiki_changed)
        self.form.wikiName.textEdited.connect(self.wiki_name_changed)

        self.current_wiki_index = 0
        self.wikis = []

        self._loadConfig()

    def _loadConfig(self) -> None:
        self.conf = self.mw.addonManager.getConfig(__name__)
        for name, value in self.conf.items():
            control = getattr(self.form, name + '_', None)
            if control is not None:
                control.setText(value)
                control.setCursorPosition(0)
        self.deckChooser.setDeckName(self.conf['defaultDeck'])
        self.wikis = [[name, config] for name, config in self.conf['wikis'].items()]
        self._populateWikiList()

    def _saveConfig(self) -> None:
        for name in list(self.conf.keys()):
            control = getattr(self.form, name + '_', None)
            if control is not None:
                self.conf[name] = control.text()
        self.conf['defaultDeck'] = self.deckChooser.deckName()

        self.conf['wikis'].clear()
        self.wiki_changed(self.current_wiki_index)  # to save changes to list
        for wiki_name, wiki_conf in self.wikis:
            self.conf['wikis'][wiki_name] = wiki_conf

        self.mw.addonManager.writeConfig(__name__, self.conf)

    def _populateWikiList(self) -> None:
        oldBlockSignals = self.form.wikiList.blockSignals(True)
        self.form.wikiList.clear()
        for wiki_name, _ in self.wikis:
            self.form.wikiList.addItem(wiki_name)
        self.form.wikiList.setCurrentRow(self.current_wiki_index)
        self.form.wikiList.blockSignals(oldBlockSignals)
        self.wiki_changed(self.current_wiki_index, save=False)

    def accept(self):
        self._saveConfig()
        super().accept()

    def get_help(self):
        pass

    def add_wiki(self) -> None:
        self._save_wiki_values()

        prototype = copy.copy(self.wikis[-1][1])
        for k in prototype.keys():
            prototype[k] = ''
        prototype['type'] = 'file'
        prototype['contentFilter'] = '[type[text/vnd.tiddlywiki]] [type[]] +[!is[system]]'
        self.wikis.append(['', prototype])

        self.current_wiki_index = len(self.wikis) - 1
        self._populateWikiList()
        self.form.wikiName.setFocus()

    def delete_wiki(self) -> None:
        if len(self.wikis) == 1:
            showWarning("You cannot delete the only configured wiki.")
            return

        if not askUser(
            "Deleting a wiki from your wiki list will cause all of the TiddlyRemember "
            "notes therein to be PERMANENTLY DELETED from your Anki collection "
            "on next sync with loss of all associated scheduling information "
            "(unless they've been moved to another wiki and retain the same IDs). "
            "If you want to preserve these notes in Anki but break the connection "
            "to the wiki, change them to a different note type in the browser first. "
            "\n\nDo you wish to continue?"):
            return

        oldBlockSignals = self.form.wikiList.blockSignals(True)
        self.form.wikiList.takeItem(self.current_wiki_index)
        del self.wikis[self.current_wiki_index]
        self.current_wiki_index = (self.current_wiki_index - 1
                                   if self.current_wiki_index != 0
                                   else 0)
        self.form.wikiList.blockSignals(oldBlockSignals)
        self.wiki_changed(self.current_wiki_index, save=False)

    def browse_for_wiki(self):
        pass

    def _save_wiki_values(self):
        current_wiki = self.wikis[self.current_wiki_index]
        current_wiki[0] = self.form.wikiName.text()
        for name in list(current_wiki[1].keys()):
            if getattr(self.form, name + '_', None):
                control = getattr(self.form, name + '_')
                if isinstance(control, QComboBox):
                    current_wiki[1][name] = control.currentText().lower()
                else:
                    current_wiki[1][name] = control.text()

    def wiki_changed(self, new_index: int, save=True):
        if save:
            # Don't do this the first time or when deleting a wiki
            # or we'll wipe out the settings for the new wiki.
            self._save_wiki_values()

        # Repopulate group box with new values.
        self.current_wiki_index = new_index
        wiki_name, wiki_config = self.wikis[new_index]
        self.form.wikiName.setText(wiki_name)
        for name, value in wiki_config.items():
            if getattr(self.form, name + '_', None):
                control = getattr(self.form, name + '_')
                if isinstance(control, QComboBox):
                    index = control.findText(value.title() if value != 'url' else 'URL')
                    if index == -1:
                        raise Exception(f"Oops, configuration for wiki URL was "
                                        f"{value}, which is not supported.")
                    control.setCurrentIndex(index)
                else:
                    control.setText(value)
                    control.setCursorPosition(0)

    def wiki_name_changed(self, new_text: str) -> None:
        self.wikis[self.current_wiki_index][0] = new_text
        self.form.wikiList.currentItem().setText(new_text)

    def type_changed(self, new_text: str) -> None:
        if new_text == 'URL':
            self.form.pathLabel.setText("&URL")
            self.form.browseButton.hide()
        else:
            self.form.pathLabel.setText("&Path")
            self.form.browseButton.show()

    def test_executable(self) -> None:
        try:
            QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
            args = [self.form.tiddlywikiBinary_.text(), "--version"]
            proc = subprocess.run(args, check=True, stderr=subprocess.STDOUT,
                                  stdout=subprocess.PIPE)
        except FileNotFoundError:
            QApplication.restoreOverrideCursor()
            showCritical("It doesn't look like that file exists on your computer. "
                         "Try using the full path to 'tiddlywiki'.")
        except subprocess.CalledProcessError as e:
            QApplication.restoreOverrideCursor()
            showCritical(
                f"It's not quite working yet. Try seeing if you can run TiddlyWiki "
                f"from the command line and copy your command in here.\n\n"
                f"{e.output}")
        else:
            QApplication.restoreOverrideCursor()
            showInfo(f"Successfully called TiddlyWiki {proc.stdout.decode().strip()}! "
                     f"You're all set.")


def edit_settings():
    dlg = SettingsDialog()
    dlg.exec_()