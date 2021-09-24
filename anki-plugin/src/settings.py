"""
settings.py - user-interface classes to help the user manage the add-on's configuration

Underneath, this is just a JSON file, using Anki's standard add-on
configuration system. We attach to some nifty hooks Anki includes to allow
the user to edit the file using a friendly GUI.
"""
import copy
import os
import platform
import subprocess
from typing import Any, List, Sequence

# pylint: disable=no-name-in-module
import aqt
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QComboBox, QApplication, QFileDialog
from PyQt5.QtGui import QCursor, QDesktopServices
from PyQt5.QtCore import QUrl
from aqt.utils import showWarning, showInfo, showCritical, askUser

from . import settings_dialog
from .util import nowin_startupinfo, DEFAULT_FILTER


class SettingsDialog(QDialog):
    """
    Friendly interface to the add-on's JSON config. Lets you specify general options
    and details of which wikis to sync.
    """
    def __init__(self) -> None:
        super().__init__()
        assert aqt.mw is not None, "Settings dialog launched before Anki initialized!"
        self.mw: aqt.AnkiQt = aqt.mw
        self.form = settings_dialog.Ui_Dialog()
        self.form.setupUi(self)

        self.deckChooser = aqt.deckchooser.DeckChooser(self.mw, self.form.deckWidget,
                                                       label=False)
        self.form.defaultDeckLabel.setBuddy(self.deckChooser.deck)

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
        self.form.wikiName.editingFinished.connect(self.prevent_duplicate_name)

        self.current_wiki_index = 0
        # Unfortunately you cannot specify a list with elements of fixed type, like
        # with Tuple. We can't use tuples because we need mutability.
        self.wikis: List[List[Any]] = []

        self._load_config()


    ##### Private helper methods. #####
    def _init_tiddlywiki_path(self) -> None:
        "If no TiddlyWiki path is defined, try to guess one."
        if os.name == 'nt':
            tw_path = os.path.expandvars("$APPDATA\\npm\\tiddlywiki.cmd")
        else:
            tw_path = 'tiddlywiki'
        self.conf['tiddlywikiBinary'] = tw_path


    def _load_config(self) -> None:
        "Populate the dialog from the add-on's config as stored by Anki."
        conf = self.mw.addonManager.getConfig(__name__)
        assert conf is not None, \
            "No config received from addon manager despite registration!"
        self.conf = conf

        if not self.conf['tiddlywikiBinary'].strip():
            self._init_tiddlywiki_path()

        for name, value in self.conf.items():
            control = getattr(self.form, name + '_', None)
            if control is not None:
                control.setText(value)
                control.setCursorPosition(0)

        if did := self.mw.col.decks.id_for_name(self.conf['defaultDeck']):
            self.deckChooser.selected_deck_id = did
        self.wikis = [[name, config] for name, config in self.conf['wikis'].items()]
        self._populate_wiki_list()

    def _save_config(self) -> None:
        "Dump the values in the dialog to the add-on's config as stored by Anki."
        for name in list(self.conf.keys()):
            control = getattr(self.form, name + '_', None)
            if control is not None:
                self.conf[name] = control.text()
        self.conf['defaultDeck'] = self.deckChooser.selected_deck_name()

        self.conf['wikis'].clear()
        self.wiki_changed(self.current_wiki_index)  # to save changes to list
        for wiki_name, wiki_conf in self.wikis:
            self.conf['wikis'][wiki_name] = wiki_conf

        self.mw.addonManager.writeConfig(__name__, self.conf)

    def _populate_wiki_list(self) -> None:
        "Update the list widget of wikis to match the self.wikis list."
        oldBlockSignals = self.form.wikiList.blockSignals(True)
        self.form.wikiList.clear()
        for wiki_name, _ in self.wikis:
            self.form.wikiList.addItem(wiki_name)
        self.form.wikiList.setCurrentRow(self.current_wiki_index)
        self.form.wikiList.blockSignals(oldBlockSignals)
        self.wiki_changed(self.current_wiki_index, save=False)

    def _load_wiki_values(self, new_index: int) -> None:
        """
        Load values from the self.wikis list to populate the wiki settings
        group box.
        """
        self.current_wiki_index = new_index
        wiki_name, wiki_config = self.wikis[new_index]
        self.form.wikiName.setText(wiki_name)
        for name, value in wiki_config.items():
            if getattr(self.form, name + '_', None):
                control = getattr(self.form, name + '_')
                if isinstance(control, QComboBox):
                    index = control.findText(value.title() if value != 'url' else 'URL')
                    if index == -1:
                        raise Exception(f"Oops, configuration for wiki type was "
                                        f"{value}, which is not supported.")
                    control.setCurrentIndex(index)
                else:
                    control.setText(value)
                    control.setCursorPosition(0)

    def _save_wiki_values(self) -> None:
        """
        Save the values the user entered for a given wiki to an entry in the
        self.wikis list.
        """
        current_wiki = self.wikis[self.current_wiki_index]
        current_wiki[0] = self.form.wikiName.text()
        for name in list(current_wiki[1].keys()):
            if getattr(self.form, name + '_', None):
                control = getattr(self.form, name + '_')
                if isinstance(control, QComboBox):
                    current_wiki[1][name] = control.currentText().lower()
                else:
                    current_wiki[1][name] = control.text()


    ##### Event handlers for buttons. #####
    def accept(self):
        "Dump new configuration and exit."
        self._save_config()
        super().accept()

    def add_wiki(self) -> None:
        "Add a new wiki to the list."
        self._save_wiki_values()

        prototype = copy.copy(self.wikis[-1][1])
        for k in prototype.keys():
            prototype[k] = ''
        prototype['type'] = 'file'
        prototype['password'] = ''
        prototype['contentFilter'] = DEFAULT_FILTER
        self.wikis.append(['', prototype])

        self.current_wiki_index = len(self.wikis) - 1
        self._populate_wiki_list()
        if platform.system() == 'Darwin':
            # Work around a weird framework bug where the group box doesn't refresh...
            # but only on MacOS. Last tested with Qt 5.13.1/PyQt 5.14.1.
            self.form.groupBox.hide()
            self.form.groupBox.show()
        self.form.wikiName.setFocus()

    def browse_for_wiki(self):
        "Use a file browser dialog to replace the path to a wiki."
        dlg = QFileDialog(self,
                          caption="Browse for wiki",
                          filter="HTML files (*.html);;All files (*)")
        if self.form.type_.currentText().lower() == 'folder':
            mode = QFileDialog.Directory
        else:
            mode = QFileDialog.ExistingFile
        dlg.setFileMode(mode)

        retval = dlg.exec_()
        if retval != 0:
            filename = dlg.selectedFiles()[0]
            self.form.path_.setText(filename)

    def delete_wiki(self) -> None:
        "Remove the selected wiki from the configuration."
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

    @staticmethod
    def get_help() -> None:
        "Launch the documentation for this dialog in a browser."
        url = QUrl(r"https://sobjornstad.github.io/TiddlyRemember/#Configuring%20the%20Anki%20add-on")
        QDesktopServices.openUrl(url)


    ##### Other event handlers. #####
    def prevent_duplicate_name(self) -> None:
        "Prevent the same name being entered for two wikis, even for a moment."
        wiki_names = [name for name, _ in self.wikis]
        if len(set(wiki_names)) != len(wiki_names):
            showWarning("Two wikis cannot have the same name. Fixing this for you.")
            new_name = _uniquify_name(self.form.wikiName.text(), wiki_names)
            self.form.wikiName.setText(new_name)
            self.wiki_name_changed(new_name)

    def test_executable(self) -> None:
        "Check to see if the TiddlyWiki executable provided can be called from Anki."
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        try:
            args = [self.form.tiddlywikiBinary_.text(), "--version"]
            proc = subprocess.run(args, check=True, stderr=subprocess.STDOUT,
                                  stdout=subprocess.PIPE,
                                  startupinfo=nowin_startupinfo())
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
        except Exception:
            QApplication.restoreOverrideCursor()
            raise
        else:
            QApplication.restoreOverrideCursor()
            showInfo(f"Successfully called TiddlyWiki {proc.stdout.decode().strip()}! "
                     f"You're all set.")

    def type_changed(self, new_text: str) -> None:
        "Adjust the interface appropriately for selection of path or URL."
        if new_text == 'URL':
            self.form.pathLabel.setText("&URL")
            self.form.browseButton.hide()
        else:
            self.form.pathLabel.setText("&Path")
            self.form.browseButton.show()

        password_possible = new_text in ('URL', 'File')
        self.form.password_.setHidden(not password_possible)
        self.form.passwordLabel.setHidden(not password_possible)
        if not password_possible:
            self.form.password_.setText("")

    def wiki_changed(self, new_index: int, save=True) -> None:
        "Save and repopulate the settings interface for the current wiki."
        if save:
            # Don't do this the first time or when deleting a wiki
            # or we'll wipe out the settings for the new wiki.
            self._save_wiki_values()

        # Repopulate group box with new values.
        self._load_wiki_values(new_index)

    def wiki_name_changed(self, new_text: str) -> None:
        "Update the wiki list when the name of a wiki changes."
        self.wikis[self.current_wiki_index][0] = new_text
        self.form.wikiList.currentItem().setText(new_text)


def _uniquify_name(name: str, names: Sequence[str]) -> str:
    """
    Given a tentative name and a list of existing names, return a possibly
    modified new name that is guaranteed not to be the same as any of the existing
    names.
    """
    number = 2
    while f"{name} {number}" in names:
        number += 1
    return f"{name} {number}"


def edit_settings() -> None:
    "Use the SettingsDialog to adjust user configuration."
    dlg = SettingsDialog()
    dlg.exec_()
