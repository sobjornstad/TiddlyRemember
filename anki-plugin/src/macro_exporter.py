"""
macro_exporter.py - Export TiddlyRemember macros from compatible Anki notes
"""

from __future__ import annotations

from anki.exporting import Exporter
from anki.collection import Collection

from . import twnote

class TiddlyRememberMacroExporter(Exporter):
    """
    Export notes of a compatible type (the TiddlyRemember type) to a text file of
    TiddlyRemember macros, so they can be easily sent over into someone else's wiki.
    Notes that are in the deck chosen to export but aren't in TiddlyRemember format
    will be ignored.
    """
    ext = ".tid"

    def __init__(self, col) -> None:
        Exporter.__init__(self, col)
        self.count = -1  # number of items exported, to report back to the UI

    @staticmethod
    def key(col: Collection) -> str:
        return "TiddlyRemember notes"

    def doExport(self, path) -> None:
        cids = sorted(self.cardIds())
        notes = set(self.col.get_card(c).note() for c in cids)

        out = []
        for n in notes:
            anki_note_type = n.note_type()
            assert anki_note_type is not None, "Note type of existing note was None!"
            tw_note_type = twnote.by_name(anki_note_type['name'])
            if tw_note_type is not None:
                out.append(tw_note_type.export_macro(n))

        self.count = len(out)
        path.write('\n\n'.join(out).encode("utf-8"))

MACRO_EXPORTER_PROPERTIES = ("TiddlyRemember macros (*.tid)",
                             TiddlyRememberMacroExporter)
