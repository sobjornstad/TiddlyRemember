"""
twnote.py - class definitions for TiddlyWiki notes

TiddlyWiki note instances extract and store the data from the rendered HTML
representation of a TiddlyWiki (see twimport.py).
"""
from abc import ABCMeta, abstractmethod, abstractclassmethod
from typing import Any, List, Optional, Set, Tuple
from urllib.parse import quote as urlquote

from anki.notes import Note
import aqt
from bs4 import BeautifulSoup

from .clozeparse import ankify_clozes
from .trmodels import TiddlyRememberQuestionAnswer, TiddlyRememberCloze, ID_FIELD_NAME
from .util import Twid


class TwNote(metaclass=ABCMeta):
    """
    One TiddlyRemember note defined in TiddlyWiki.

    This abstract class provides common functionality that different types of
    notes will need to use. A subclass is used for each type of note (e.g.,
    Q&A, cloze).
    
    Each TwNote subclass has a one-to-one relationship to a specific Anki
    model (note type), defined in the trmodels.py file. This relationship is
    determined by the /model/ class variable.

    TwNotes are always created by the factory method
    TwNote.notes_from_soup(), which allows each subclass to construct one or
    more instances of itself from a tiddler's text using the parse_html
    factory method, if it returns True from its wants_soup() classmethod when
    passed that tiddler's text. Thus, any number of TiddlyWiki note types can be
    added without having to change any other code, and types can be freely mixed
    within a tiddler.

    In addition to the class variable and two classmethods described above,
    each subclass must override the template instance methods _fields_equal()
    and _update_fields(), which define when and how Anki notes are created
    and updated from this TiddlyWiki note; see their docstrings for details.
    """
    model: Any = None  #: The ModelData class for the Anki note generated by this type

    def __init__(self, id_: Twid, wiki_name: str, tidref: str, 
                 target_tags: Set[str], target_deck: Optional[str]) -> None:
        self.id_ = id_
        self.wiki_name = wiki_name
        self.tidref = tidref
        self.target_tags = target_tags
        self.target_deck = target_deck
        self.permalink: Optional[str] = None

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)

    @classmethod
    def notes_from_soup(cls, soup: BeautifulSoup,
                        wiki_name: str, tiddler_name: str) -> Set['TwNote']:
        """
        Given soup for a tiddler and the tiddler's name, create notes by calling
        the wants_soup and parse_html methods of each candidate subclass.
        """
        notes: Set[TwNote] = set()
        for subclass in cls.__subclasses__():
            wanted_soup = subclass.wants_soup(soup)  # type: ignore
            if wanted_soup:
                notes.update(subclass.parse_html(soup, wiki_name, tiddler_name))  # type: ignore
        return notes

    def _assert_correct_model(self, anki_note: Note) -> None:
        """
        Raise an assertion error if the :attr:`anki_note` doesn't match
        the current class's model.
        """
        # pylint: disable=no-member
        assert self.model_equal(anki_note), \
            f"Expected note of type {self.model.name}, but got {anki_note.model()['name']}."  # type: ignore

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
        self._assert_correct_model(anki_note)
        return self._fields_equal(anki_note)

    def model_equal(self, anki_note: Note) -> bool:
        """
        Compare the model (note type) defined for this TwNote to that of
        an Anki note. Return True if it is the same model.
        """
        model = anki_note.model()
        assert model is not None, "Anki note passed does not have a model!"
        assert self.model is not None, \
             f"Class {self.__class__} does not specify a 'model' attribute."
        return model['name'] == self.model.name

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
        self._assert_correct_model(anki_note)
        self._update_fields(anki_note)


    ### Abstract methods ###
    @abstractclassmethod
    def parse_html(cls, soup: BeautifulSoup, wiki_name: str, tiddler_name: str):
        """
        Given soup and the name of the wiki and its tiddler, construct and return
        any TwNotes of this subclass's type that can be extracted from it.
        """
        raise NotImplementedError

    @abstractclassmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:
        """
        Whether this subclass wants an opportunity to parse the provided
        :attr:`soup` and return TwNotes of its type through the parse_html() method;
        presumably, true if there are any notes of the provided type in the soup.
        """
        raise NotImplementedError

    @abstractmethod
    def _fields_equal(self, anki_note: Note) -> bool:
        "Check whether this TwNote's fields match those of the provided Anki note."
        raise NotImplementedError

    @abstractmethod
    def _update_fields(self, anki_note: Note) -> None:
        """
        Update the fields of the provided Anki note to match those of this TwNote.

        This function is used both when creating new notes (just after
        defining a blank note and its model) and when updating existing notes.
        """
        raise NotImplementedError


class QuestionNote(TwNote):
    "A question-and-answer pair, much like Anki's Basic note type."
    model = TiddlyRememberQuestionAnswer

    def __init__(self, id_: Twid, wiki_name: str, tidref: str,
                 question: str, answer: str,
                 target_tags: Set[str], target_deck: Optional[str]) -> None:
        super().__init__(id_, wiki_name, tidref, target_tags, target_deck)
        self.question = question
        self.answer = answer

    def __repr__(self):
        return (f"QuestionNote(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"question={self.question!r}, answer={self.answer!r}, "
                f"target_tags={self.target_tags!r}, target_deck={self.target_deck!r})")

    @classmethod
    def parse_html(cls, soup: BeautifulSoup, wiki_name: str,
                   tiddler_name: str) -> Set['QuestionNote']:
        notes = set()
        deck, tags = _get_deck_and_tags(soup)

        pairs = soup.find_all("div", class_="rememberq")
        for pair in pairs:
            question = pair.find("div", class_="rquestion").p.get_text()
            answer = pair.find("div", class_="ranswer").p.get_text()
            id_raw = pair.find("div", class_="rid").get_text()
            id_ = id_raw.strip().lstrip('[').rstrip(']')
            tidref = select_tidref(pair.find("div", class_="tr-reference"),
                                   tiddler_name)
            notes.add(cls(id_, wiki_name, tidref, question, answer, tags, deck))

        return notes

    @classmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:
        return bool(soup.find("div", class_="rememberq"))

    def _fields_equal(self, anki_note: Note) -> bool:
        return (
            self.question == anki_note['Question']
            and self.answer == anki_note['Answer']
            and self.id_ == anki_note[ID_FIELD_NAME]
            and self.wiki_name == anki_note['Wiki']
            and self.tidref == anki_note['Reference']
            and (self.permalink or "") == anki_note['Permalink']
            and self.anki_tags == anki_note.tags
        )

    def _update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        anki_note['Question'] = self.question
        anki_note['Answer'] = self.answer
        anki_note['Wiki'] = self.wiki_name
        anki_note['Reference'] = self.tidref
        anki_note['Permalink'] = self.permalink if self.permalink is not None else ""
        anki_note[ID_FIELD_NAME] = self.id_
        anki_note.tags = self.anki_tags


class ClozeNote(TwNote):
    "A cloze deletion-based note, much like Anki's built-in Cloze note type."
    model = TiddlyRememberCloze

    def __init__(self, id_: Twid, wiki_name: str, tidref: str, text: str,
                 target_tags: Set[str], target_deck: Optional[str]) -> None:
        super().__init__(id_, wiki_name, tidref, target_tags, target_deck)
        self.text = text

    def __repr__(self):
        return (f"ClozeNote(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"text={self.text!r}, target_tags={self.target_tags!r}, "
                f"target_deck={self.target_deck!r})")

    @classmethod
    def parse_html(cls, soup: BeautifulSoup, wiki_name: str,
                   tiddler_name: str) -> Set['ClozeNote']:
        notes = set()
        deck, tags = _get_deck_and_tags(soup)

        pairs = soup.find_all(class_="remembercz")
        for pair in pairs:
            text = pair.find("span", class_="cloze-text").get_text()
            id_raw = pair.find("div", class_="rid").get_text()
            id_ = id_raw.strip().lstrip('[').rstrip(']')
            tidref = select_tidref(pair.find("div", class_="tr-reference"),
                                   tiddler_name)
            parsed_text = ankify_clozes(text)
            notes.add(cls(id_, wiki_name, tidref, parsed_text, tags, deck))

        return notes

    @classmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:
        return bool(soup.find("div", class_="remembercz"))

    def _fields_equal(self, anki_note: Note) -> bool:
        return (
            self.text == anki_note['Text']
            and self.id_ == anki_note[ID_FIELD_NAME]
            and self.wiki_name == anki_note['Wiki']
            and self.tidref == anki_note['Reference']
            and (self.permalink or "") == anki_note['Permalink']
            and self.anki_tags == anki_note.tags
        )

    def _update_fields(self, anki_note: Note) -> None:
        anki_note['Text'] = self.text
        anki_note[ID_FIELD_NAME] = self.id_
        anki_note['Wiki'] = self.wiki_name
        anki_note['Reference'] = self.tidref
        anki_note['Permalink'] = self.permalink if self.permalink is not None else ""
        anki_note.tags = self.anki_tags


def _get_deck_and_tags(tiddler_soup: BeautifulSoup) -> Tuple[Optional[str], Set[str]]:
    """
    Given the soup of a tiddler, extract its deck and list of tags.
    """
    deckList = tiddler_soup.find("ul", id="anki-decks")
    if deckList:
        firstItem = deckList.find("li")
        deck = firstItem.get_text() if firstItem is not None else None
    else:
        deck = None

    tagList = tiddler_soup.find("ul", id="anki-tags")
    if tagList:
        tags = set(i.get_text() for i in tagList.find_all("li"))
    else:
        tags = set()

    return deck, tags


def select_tidref(hard_ref: BeautifulSoup, tiddler_name: str):
    """
    Given the hard-reference BS node coming from an HTML snippet and the name
    of the tiddler the HTML snippet was rendered within, return the string to
    be used as a tiddler reference. This will be the hard-reference if the
    tr-reference div exists and is non-empty, otherwise the tiddler name.
    """
    if hard_ref is not None and hard_ref.get_text().strip():
        return hard_ref.get_text().strip()
    else:
        return tiddler_name
