"""
macro_exporter.py - Export TiddlyRemember macros from compatible Anki notes
"""

from __future__ import annotations

import datetime
from typing import List, Optional, Sequence

import anki.consts
from anki.cards import CardId
from anki.collection import (
    CardIdsLimit, Collection, DeckIdLimit, ExportLimit, NoteIdsLimit
)
from anki.decks import DeckId
from anki.notes import Note, NoteId
import aqt
from aqt import gui_hooks
from aqt.import_export.exporting import Exporter, ExportOptions
from aqt.operations import QueryOp
from aqt.utils import tooltip

from . import twnote
from .util import pluralize


def note_ids_for_limit(col: Collection, limit: ExportLimit) -> List[NoteId]:
    """
    Resolve the export limit chosen in Anki's export dialog into the list of
    note IDs it covers, in a stable order.
    """
    def nids_of_cards(cids: Sequence[CardId]) -> List[NoteId]:
        # dict.fromkeys dedupes (siblings share a note) while keeping order.
        return list(dict.fromkeys(col.get_card(cid).nid for cid in sorted(cids)))

    if isinstance(limit, NoteIdsLimit):
        return list(limit.note_ids)
    if isinstance(limit, CardIdsLimit):
        return nids_of_cards(limit.card_ids)
    if isinstance(limit, DeckIdLimit):
        return nids_of_cards(col.decks.cids(DeckId(limit.deck_id), children=True))
    return nids_of_cards(col.find_cards(""))


def schedule_string(col: Collection, note: Note) -> Optional[str]:
    """
    Given a note, return a 'sched' string representing its scheduling info
    if it's a review card, or None otherwise.
    """
    c = note.cards()[0]

    if c.type == anki.consts.CARD_TYPE_REV:
        due_days_from_today = c.due - col.sched.today
        due_date = (datetime.datetime.now().date()
                    + datetime.timedelta(days=due_days_from_today))
        due_str = due_date.strftime(r"%Y%m%d1200000")
        return f"due:{due_str};ivl:{c.ivl};ease:{c.factor};lapses:{c.lapses}"
    else:
        return None


def macros_for_notes(col: Collection, note_ids: Sequence[NoteId],
                     include_scheduling: bool) -> List[str]:
    """
    Render the TiddlyRemember macros for all notes in /note_ids/ that use a
    TiddlyRemember note type. Notes of other types are silently skipped.
    """
    out = []
    for nid in note_ids:
        n = col.get_note(nid)
        anki_note_type = n.note_type()
        assert anki_note_type is not None, "Note type of existing note was None!"
        tw_note_type = twnote.by_name(anki_note_type['name'])
        if tw_note_type is not None:
            schedule_str = schedule_string(col, n) if include_scheduling else ""
            out.append(tw_note_type.export_macro(n, schedule_str))
    return out


def export_macro_file(col: Collection, options: ExportOptions) -> int:
    "Write the macro file described by /options/, returning the note count."
    macros = macros_for_notes(col,
                              note_ids_for_limit(col, options.limit),
                              options.include_scheduling)
    with open(options.out_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(macros))
    return len(macros)


class TiddlyRememberMacroExporter(Exporter):
    """
    Export notes of a compatible type (the TiddlyRemember type) to a text file of
    TiddlyRemember macros, so they can be easily sent over into someone else's wiki.
    Notes that are in the deck chosen to export but aren't in TiddlyRemember format
    will be ignored.
    """
    extension = "tid"
    show_deck_list = True
    show_include_scheduling = True

    @staticmethod
    def name() -> str:
        return "TiddlyRemember macros"

    def export(self, mw: aqt.main.AnkiQt, options: ExportOptions) -> None:
        options = gui_hooks.exporter_will_export(options, self)
        # ExportOptions gained a 'parent' field in Anki 26.09.
        parent = getattr(options, 'parent', None) or mw

        def on_success(count: int) -> None:
            gui_hooks.exporter_did_export(options, self)
            tooltip(f"Exported {count} {pluralize('note', count)}.",
                    parent=parent)

        QueryOp(
            parent=parent,
            op=lambda col: export_macro_file(col, options),
            success=on_success,
        ).run_in_background()
