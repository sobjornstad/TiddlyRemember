from abc import ABCMeta, abstractmethod
from typing import Any, List, Optional, Set
from urllib.parse import quote as urlquote

from anki.notes import Note
import aqt

from .trmodels import TiddlyRememberQuestionAnswer
from .util import Twid

class TwNote(metaclass=ABCMeta):
    model: Any = None

    def __init__(self, id_: Twid, tidref: str, 
                 target_tags: Set[str], target_deck: Optional[str]) -> None:
        self.id_ = id_
        self.tidref = tidref
        self.target_tags = target_tags
        self.target_deck = target_deck
        self.permalink: Optional[str] = None

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)

    @abstractmethod
    def _subclass_fields_equal(self, anki_note: Note) -> bool:
        "Check field equality for the given note type."
        raise NotImplementedError

    @property
    def anki_tags(self) -> List[str]:
        """
        Munge tags and return a list suitable for use in Anki.

        A quick test shows most if not all special characters are valid in tags;
        I cannot find further documentation on any issues these may cause.
        Spaces aren't, though, since tags are separated by spaces.
        """
        assert aqt.mw is not None, "Anki not initialized prior to TiddlyWiki sync!"
        # Canonify seems to be returning empty strings as part of the list,
        # perhaps due to a bug. Strip them so our equality checks don't get
        # goofed up.
        canon = aqt.mw.col.tags.canonify(
            [t.replace(' ', '_') for t in self.target_tags])
        return [i for i in canon if i.strip()]

    def fields_equal(self, anki_note: Note) -> bool:
        """
        Compare the fields on this TwNote to an Anki note. Return True if all
        are equal.
        """
        # pylint: disable=no-member
        model = anki_note.model()
        assert model is not None
        assert model['name'] == self.model.name, \
             f"Expected note of type {self.model.name}, but got {model['name']}."

        return self._subclass_fields_equal(anki_note)

    def set_permalink(self, base_url: str) -> None:
        """
        Build and add the permalink field to this note given the base URL of
        the wiki. May be used to replace an existing permalink.
        """
        if not base_url.endswith('/'):
            base_url += '/'
        self.permalink = base_url + "#" + urlquote(self.tidref)

    @abstractmethod
    def update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        raise NotImplementedError


class QuestionNote(TwNote):
    model = TiddlyRememberQuestionAnswer

    def __init__(self, id_: Twid, tidref: str, question: str, answer: str,
                 target_tags: Set[str], target_deck: Optional[str]) -> None:
        super().__init__(id_, tidref, target_tags, target_deck)
        self.question = question
        self.answer = answer

    def __repr__(self):
        return (f"TwNote(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"question={self.question!r}, answer={self.answer!r}, "
                f"target_tags={self.target_tags!r}, target_deck={self.target_deck!r})")

    def _subclass_fields_equal(self, anki_note):
        return (
            self.question == anki_note.fields[0]
            and self.answer == anki_note.fields[1]
            and self.id_ == anki_note.fields[2]
            and self.tidref == anki_note.fields[3]
            and self.permalink == anki_note.fields[4]
            and self.anki_tags == anki_note.tags
        )

    def update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        anki_note.fields[0] = self.question
        anki_note.fields[1] = self.answer
        anki_note.fields[3] = self.tidref
        anki_note.fields[4] = self.permalink if self.permalink is not None else ""
        anki_note['Reference'] = self.tidref
        anki_note.tags = self.anki_tags
