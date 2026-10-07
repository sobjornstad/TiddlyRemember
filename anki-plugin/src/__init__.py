###################################################################
# TiddlyRemember - store Anki notes in a NodeJS TiddlyWiki
# Copyright 2020--2021 Soren Bjornstad <contact@sorenbjornstad.com>
# and the TiddlyRemember community.
###################################################################

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

"""
__init__.py -- set up the add-on
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

import aqt
from aqt.utils import showWarning
# pylint: disable=import-error, no-name-in-module
from aqt.qt import QAction, QKeySequence

from .importer import ImportDialog
from .macro_exporter import TiddlyRememberMacroExporter
from .settings import edit_settings
from .twnote import TwNote

if TYPE_CHECKING:
    from anki.models import NoteType


def begin_sync() -> None:
    "Launch the importer dialog."
    dialog = ImportDialog(aqt.mw)
    if dialog.start_import():
        dialog.exec()


def register_note_type_warning() -> None:
    "Remind the user not to add notes of the TiddlyRemember note type."
    def warn_if_adding_tiddlyremember(note_type_name: str) -> None:
        if note_type_name in (i.model.name for i in TwNote.note_types()):
            showWarning(
                f"You are adding notes using the '{note_type_name}' note type. "
                f"TiddlyRemember notes added directly within Anki "
                f"will be permanently deleted on the next TiddlyRemember sync. "
                f"Unless you're sure you know what you're doing, "
                f"please select a different note type.")

    def on_change_note_type(_old: NoteType, new: NoteType) -> None:
        warn_if_adding_tiddlyremember(new['name'])

    def on_add_init(add_cards_dialog: Any) -> None:
        # Anki 26.09's experimental Add dialog (NewAddCards) has no
        # notetype_chooser, so there's nothing we can check there yet.
        chooser = getattr(add_cards_dialog, 'notetype_chooser', None)
        if chooser is not None:
            warn_if_adding_tiddlyremember(chooser.selected_notetype_name())

    aqt.gui_hooks.add_cards_did_change_note_type.append(on_change_note_type)
    aqt.gui_hooks.add_cards_did_init.append(on_add_init)


if aqt.mw is not None:
    # Set up menu option to begin a sync.
    action = QAction(aqt.mw)
    action.setText("Sync from &TiddlyWiki")
    action.setShortcut(QKeySequence("Shift+Y"))
    aqt.mw.form.menuTools.addAction(action)
    action.triggered.connect(begin_sync)  # type: ignore

    # Set up config dialog.
    aqt.mw.addonManager.setConfigAction(__name__, edit_settings)

    # Set up reminder message when user selects the TR note type to add notes.
    register_note_type_warning()

    # Set up macro exporter.
    def add_exporter(exporters):
        exporters.append(TiddlyRememberMacroExporter)
    aqt.gui_hooks.exporters_list_did_initialize.append(add_exporter)
