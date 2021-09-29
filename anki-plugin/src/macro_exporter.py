"""
macro_exporter.py - Export TiddlyRemember macros from compatible Anki notes
"""

from __future__ import annotations

import datetime
from typing import Optional

import anki.consts
from anki.collection import Collection
from anki.exporting import Exporter
from anki.notes import Note

from . import twnote

class TiddlyRememberMacroExporter(Exporter):
    """
    Export notes of a compatible type (the TiddlyRemember type) to a text file of
    TiddlyRemember macros, so they can be easily sent over into someone else's wiki.
    Notes that are in the deck chosen to export but aren't in TiddlyRemember format
    will be ignored.
    """
    ext = ".tid"
    includeSched = False

    def __init__(self, col) -> None:
        Exporter.__init__(self, col)
        self.count = -1  # number of items exported, to report back to the UI

    @staticmethod
    def key(col: Collection) -> str:
        return "TiddlyRemember notes"

    def sched(self, note: Note) -> Optional[str]:
        """
        Given a note, return a 'sched' string representing its scheduling info
        if it's a review card, or None otherwise.
        """
        c = note.cards()[0]

        if c.type == anki.consts.CARD_TYPE_REV:
            due_days_from_today = c.due - self.col.sched.today
            due_date = (datetime.datetime.now().date()
                        + datetime.timedelta(days=due_days_from_today))
            due_str = due_date.strftime(r"%Y%m%d1200000")
            return f"due:{due_str};ivl:{c.ivl};ease:{c.factor};lapses:{c.lapses}"
        else:
            return None

    def doExport(self, path) -> None:
        cids = sorted(self.cardIds())
        nids = set(self.col.get_card(c).note().id for c in cids)
        notes = set(self.col.get_note(i) for i in nids)

        out = []
        for n in notes:
            anki_note_type = n.note_type()
            assert anki_note_type is not None, "Note type of existing note was None!"
            tw_note_type = twnote.by_name(anki_note_type['name'])
            if tw_note_type is not None:
                schedule_str = self.sched(n) if self.includeSched else ""
                out.append(tw_note_type.export_macro(n, schedule_str))

        self.count = len(out)
        path.write('\n\n'.join(out).encode("utf-8"))

MACRO_EXPORTER_PROPERTIES = ("TiddlyRemember macros (*.tid)",
                             TiddlyRememberMacroExporter)
