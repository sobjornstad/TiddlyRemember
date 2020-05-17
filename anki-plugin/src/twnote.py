from typing import List, Optional, Set
from urllib.parse import quote as urlquote

from anki.notes import Note
import aqt

from .util import Twid

class TwNote:
    def __init__(self, id_: Twid, tidref: str, question: str, answer: str,
                 target_tags: Set[str], target_deck: Optional[str]) -> None:
        self.id_ = id_
        self.tidref = tidref
        self.question = question
        self.answer = answer
        self.target_tags = target_tags
        self.target_deck = target_deck
        self.permalink: Optional[str] = None

    def __repr__(self):
        return (f"Note(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"question={self.question!r}, answer={self.answer!r}")

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)

    @property
    def anki_tags(self) -> List[str]:
        """
        Munge tags and return a list suitable for use in Anki.

        A quick test shows most if not all special characters are valid in tags;
        I cannot find further documentation on any issues these may cause.
        Spaces aren't, though, since tags are separated by spaces.
        """
        assert aqt.mw is not None, "Anki not initialized prior to TiddlyWiki sync!"
        return aqt.mw.col.tags.canonify(
            [t.replace(' ', '_') for t in self.target_tags])

    def fields_equal(self, anki_note: Note) -> bool:
        """
        Compare the fields on this TwNote to an Anki note. Return True if all
        are equal.
        """
        return (
            self.question == anki_note.fields[0]
            and self.answer == anki_note.fields[1]
            and self.id_ == anki_note.fields[2]
            and self.tidref == anki_note.fields[3]
            and self.permalink == anki_note.fields[4]
            and self.anki_tags == anki_note.tags
        )

    def set_permalink(self, base_url: str) -> None:
        """
        Build and add the permalink field to this note given the base URL of
        the wiki. May be used to replace an existing permalink.
        """
        if not base_url.endswith('/'):
            base_url += '/'
        self.permalink = base_url + "#" + urlquote(self.tidref)

    def update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        anki_note.fields[0] = self.question
        anki_note.fields[1] = self.answer
        anki_note.fields[3] = self.tidref
        anki_note.fields[4] = self.permalink if self.permalink is not None else ""
        anki_note.tags = self.anki_tags
