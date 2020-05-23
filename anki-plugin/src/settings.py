import copy

import aqt
from aqt.qt import QAction, QThread, QKeySequence
from PyQt5.QtWidgets import QDialog, QComboBox
from PyQt5.QtCore import pyqtSignal
from aqt.utils import getFile, showWarning, askUser

from . import settings_dialog


class SettingsDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.form = settings_dialog.Ui_Dialog()
        self.form.setupUi(self)
        self.mw = aqt.mw

        self.form.okButton.clicked.connect(self.accept)
        self.form.cancelButton.clicked.connect(self.reject)
        self.form.helpButton.clicked.connect(self.get_help)
        self.form.addWikiButton.clicked.connect(self.add_wiki)
        self.form.deleteWikiButton.clicked.connect(self.delete_wiki)
        self.form.browseButton.clicked.connect(self.browse_for_wiki)
        self.form.type_.currentIndexChanged.connect(self.type_changed)
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
        self.wikis = [[name, config] for name, config in self.conf['wikis'].items()]
        self._populateWikiList()

    def _saveConfig(self) -> None:
        for name in list(self.conf.keys()):
            control = getattr(self.form, name + '_', None)
            if control is not None:
                self.conf[name] = control.text()

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

    def type_changed(self, new_index: int):
        pass


def edit_settings():
    dlg = SettingsDialog()
    dlg.exec_()