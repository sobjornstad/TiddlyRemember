"""
twnote.py - class definitions for TiddlyWiki notes

TiddlyWiki note instances extract and store the data from the rendered HTML
representation of a TiddlyWiki (see twimport.py).
"""
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import date
import hashlib
import mimetypes
from pathlib import Path
import re
from typing import Any, List, Optional, Set, Tuple, Type
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from urllib.parse import quote as urlquote

from anki.collection import Collection
from anki.notes import Note
from bs4 import BeautifulSoup

from .clozeparse import ankify_clozes
from .oops import ConfigurationError, ExtractError, ScheduleParsingError
from .trmodels import (TiddlyRememberQuestionAnswer, TiddlyRememberCloze,
                       TiddlyRememberPair, ID_FIELD_NAME)
from .util import COMPATIBLE_TW_VERSIONS, PLUGIN_VERSION, Twid, tw_quote, pushd
from .wiki import Wiki, WikiType


@dataclass
class SchedulingInfo():
    """
    Scheduling information for a card.
    """
    ivl: int
    due: date
    ease: int
    lapses: int


class TwMedia:
    """
    One media file being imported into Anki from TiddlyWiki.
    """
    def __init__(self, data: bytes, url: str, warnings: List[str]) -> None:
        self.data = data
        self.url = url
        self.hash = hashlib.sha256(data).hexdigest()

        mime_type, _ = mimetypes.guess_type(url)
        self.extension = mimetypes.guess_extension(mime_type or "")
        if self.extension is None:
            warnings.append(f"Unknown media type for URL '{url}': using extension "
                            f"'xxx'. The media may not render correctly in Anki.")
            self.extension = ".xxx"
        self.filename = "tr-" + self.hash + self.extension

    def __eq__(self, other) -> bool:
        return self.hash == other.hash

    def __hash__(self) -> int:
        return hash(self.hash)

    def __repr__(self) -> str:
        return f"TwMedia(extension={self.extension}, src={self.url}, hash={self.hash})"

    def write_to_anki(self, col: Collection) -> None:
        """
        Save the file to Anki's media folder if it isn't already there.

        Since our filenames are based on a hash of their content, we can try to
        add media as many times as we want while updating without risk of ending
        up with duplicates.  (If the user added the media directly to Anki
        themselves, then we might end up with one duplicate, but there's nothing
        we can do about that unless we want to read through the entire media
        directory and hash every file.)
        """
        assert self.extension is not None, \
            "Unable to determine filename extension to use."
        if not col.media.have(self.filename):
            col.media.write_data(desired_fname=self.filename, data=self.data)


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

    def __init__(self, id_: Twid, wiki: Wiki, tidref: str,
                 target_tags: Set[str], target_deck: Optional[str],
                 media: Optional[Set[TwMedia]],
                 schedule: Optional[SchedulingInfo]) -> None:
        self.id_ = id_
        self.wiki = wiki
        self.tidref = tidref
        self.target_tags = target_tags
        self.target_deck = target_deck
        self.permalink: Optional[str] = None
        self.schedule: Optional[SchedulingInfo] = schedule
        self.media = media or set()

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)

    @classmethod
    def note_types(cls):
        return list(cls.__subclasses__())

    @classmethod
    def notes_from_soup(cls, soup: BeautifulSoup,
                        wiki: Wiki, tiddler_name: str,
                        warnings: List[str]) -> Set['TwNote']:
        """
        Given soup for a tiddler and the tiddler's name, create notes by calling
        the wants_soup and parse_html methods of each candidate subclass.
        """
        notes: Set[TwNote] = set()
        for subclass in cls.__subclasses__():
            wanted_soup = subclass.wants_soup(soup)  # type: ignore
            if wanted_soup:
                notes.update(subclass.parse_html(
                    soup, wiki, tiddler_name, warnings))  # type: ignore
        return notes

    def _assert_correct_model(self, anki_note: Note) -> None:
        """
        Raise an assertion error if the :attr:`anki_note` doesn't match
        the current class's model.
        """
        assert self.model is not None, "TwNote subclass forgot to set self.model"
        # pylint: disable=no-member
        assert self.model_equal(anki_note), \
            (f"Expected note of type {self.model.name}, "  # type: ignore
             f"but got {anki_note.note_type()['name']}.")

    @property
    def anki_tags(self) -> List[str]:
        """
        Munge tags and return a list suitable for use in Anki.

        A quick test shows most if not all special characters are valid in tags;
        I cannot find further documentation on any issues these may cause.
        Spaces aren't, though, since tags are separated by spaces.
        """
        return [t.replace(' ', '_') for t in self.target_tags]

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
        model = anki_note.note_type()
        assert model is not None, "Anki note passed does not have a model!"
        assert self.model is not None, \
             f"Class {self.__class__} does not specify a 'model' attribute."
        return model['name'] == self.model.name

    def set_permalink(self, base_url: str) -> None:
        """
        Build and add the permalink field to this note given the base URL of
        the wiki. May be used to replace an existing permalink.
        """
        self.permalink = base_url + "#" + urlquote(self.tidref)

    def update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        self._assert_correct_model(anki_note)
        self._update_fields(anki_note)

    def _base_equal(self, anki_note: Note) -> bool:
        """
        Built-in base equality check for fields that should be the same on all types.
        Subclass must explicitly call this method if it wishes to use it.
        """
        return (
            self.id_ == anki_note[ID_FIELD_NAME]
            and self.wiki.name == anki_note['Wiki']
            and self.tidref == anki_note['Reference']
            and (self.permalink or "") == anki_note['Permalink']
            and self.anki_tags == anki_note.tags
        )

    def _base_update(self, anki_note: Note) -> None:
        """
        Built-in update functionality for fields that should be the same on all types.
        Subclass must explicitly call this method if it wishes to use it.
        """
        anki_note['Wiki'] = self.wiki.name
        anki_note['Reference'] = self.tidref
        anki_note['Permalink'] = self.permalink if self.permalink is not None else ""
        anki_note[ID_FIELD_NAME] = self.id_
        anki_note.tags = self.anki_tags


    ### Abstract methods ###
    @classmethod
    @abstractmethod
    def export_macro(cls, anki_note: Note,
                     sched: Optional[str] = None) -> str:  # pragma: no cover
        """
        Given an Anki note, return a string representation of a TiddlyWiki macro call
        which will result in an Anki card of the current note type when imported
        again through TiddlyRemember.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def parse_html(cls, soup: BeautifulSoup, wiki: Wiki, tiddler_name: str,
                   warnings: List[str]):  # pragma: no cover
        """
        Given soup and the name of the wiki and its tiddler, construct and return
        any TwNotes of this subclass's type that can be extracted from it.

        Add a message for any non-critical issues that arise to the list of warnings.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:  # pragma: no cover
        """
        Whether this subclass wants an opportunity to parse the provided
        :attr:`soup` and return TwNotes of its type through the parse_html() method;
        presumably, true if there are any notes of the provided type in the soup.
        """
        raise NotImplementedError

    @abstractmethod
    def _fields_equal(self, anki_note: Note) -> bool:  # pragma: no cover
        "Check whether this TwNote's fields match those of the provided Anki note."
        raise NotImplementedError

    @abstractmethod
    def _update_fields(self, anki_note: Note) -> None:  # pragma: no cover
        """
        Update the fields of the provided Anki note to match those of this TwNote.

        This function is used both when creating new notes (just after
        defining a blank note and its model) and when updating existing notes.
        """
        raise NotImplementedError


class QuestionNote(TwNote):
    "A question-and-answer pair, much like Anki's Basic note type."
    model = TiddlyRememberQuestionAnswer

    def __init__(self, id_: Twid, wiki: Wiki, tidref: str,
                 question: str, answer: str,
                 target_tags: Set[str], target_deck: Optional[str],
                 media: Optional[Set[TwMedia]] = None,
                 schedule: Optional[SchedulingInfo] = None) -> None:
        super().__init__(id_, wiki, tidref, target_tags, target_deck, media,
                         schedule)
        self.question = question
        self.answer = answer

    def __repr__(self):
        return (f"QuestionNote(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"question={self.question!r}, answer={self.answer!r}, "
                f"target_tags={self.target_tags!r}, target_deck={self.target_deck!r}, "
                f"schedule={self.schedule!r})")

    @classmethod
    def export_macro(cls, anki_note: Note, sched: Optional[str] = None) -> str:
        idx = cls.model.field_index_by_name
        sched_fragment = ('\n    sched:"' + sched + '"') if sched else ""
        return (
            f"<<rememberq\n"
            f'    "{anki_note.fields[idx(ID_FIELD_NAME)]}"\n'
            f"    {munge_export_field(anki_note.fields[idx('Question')])}\n"
            f"    {munge_export_field(anki_note.fields[idx('Answer')])}{sched_fragment}>>" # pylint: disable=line-too-long
        )

    @classmethod
    def parse_html(cls, soup: BeautifulSoup, wiki: Wiki,
                   tiddler_name: str, warnings: List[str]) -> Set['QuestionNote']:
        notes = set()
        deck, tags = _get_deck_and_tags(soup)

        media: Set[TwMedia] = set()
        pairs = soup.find_all("div", class_="rememberq")
        for pair in pairs:
            pair = extract_media(media, pair, wiki, tiddler_name, warnings)
            question = clean_field_html(pair.find("div", class_="rquestion").p)
            answer = clean_field_html(pair.find("div", class_="ranswer").p)
            id_raw = pair.find("div", class_="rid").get_text()
            id_ = id_raw.strip().lstrip('[').rstrip(']')
            tidref = select_tidref(pair.find("div", class_="tr-reference"),
                                   tiddler_name)
            sched = build_scheduling_info(pair, tiddler_name)
            notes.add(cls(id_, wiki, tidref, question, answer, tags, deck, media,
                          sched))

        return notes

    @classmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:
        return bool(soup.find("div", class_="rememberq"))

    def _fields_equal(self, anki_note: Note) -> bool:
        return (
            self.question == anki_note['Question']
            and self.answer == anki_note['Answer']
            and self._base_equal(anki_note)
        )

    def _update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        anki_note['Question'] = self.question
        anki_note['Answer'] = self.answer
        self._base_update(anki_note)


class PairNote(TwNote):
    "A two-sided note, much like Anki's Basic (and reversed) note type."
    model = TiddlyRememberPair

    def __init__(self, id_: Twid, wiki: Wiki, tidref: str,
                 first: str, second: str,
                 target_tags: Set[str], target_deck: Optional[str],
                 media: Optional[Set[TwMedia]] = None,
                 schedule: Optional[SchedulingInfo] = None) -> None:
        super().__init__(id_, wiki, tidref, target_tags, target_deck, media,
                         schedule)
        self.first = first
        self.second = second

    def __repr__(self):
        return (f"PairNote(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"first={self.first!r}, second={self.second!r}, "
                f"target_tags={self.target_tags!r}, target_deck={self.target_deck!r}, "
                f"schedule={self.schedule!r})")

    @classmethod
    def export_macro(cls, anki_note: Note, sched: Optional[str] = None) -> str:
        idx = cls.model.field_index_by_name
        sched_fragment = ('\n    sched:"' + sched + '"') if sched else ""
        return (
            f"<<rememberp\n"
            f'    "{anki_note.fields[idx(ID_FIELD_NAME)]}"\n'
            f"    {munge_export_field(anki_note.fields[idx('First')])}\n"
            f"    {munge_export_field(anki_note.fields[idx('Second')])}{sched_fragment}>>" # pylint: disable=line-too-long
        )

    @classmethod
    def parse_html(cls, soup: BeautifulSoup, wiki: Wiki,
                   tiddler_name: str, warnings: List[str]) -> Set['PairNote']:
        notes = set()
        deck, tags = _get_deck_and_tags(soup)

        media: Set[TwMedia] = set()
        pairs = soup.find_all("div", class_="rememberp")
        for pair in pairs:
            pair = extract_media(media, pair, wiki, tiddler_name, warnings)
            question = clean_field_html(pair.find("div", class_="rfirst").p)
            answer = clean_field_html(pair.find("div", class_="rsecond").p)
            id_raw = pair.find("div", class_="rid").get_text()
            id_ = id_raw.strip().lstrip('[').rstrip(']')
            tidref = select_tidref(pair.find("div", class_="tr-reference"),
                                   tiddler_name)
            sched = build_scheduling_info(pair, tiddler_name)
            notes.add(cls(id_, wiki, tidref, question, answer, tags, deck, media,
                          sched))

        return notes

    @classmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:
        return bool(soup.find("div", class_="rememberp"))

    def _fields_equal(self, anki_note: Note) -> bool:
        return (
            self.first == anki_note['First']
            and self.second == anki_note['Second']
            and self._base_equal(anki_note)
        )

    def _update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        anki_note['First'] = self.first
        anki_note['Second'] = self.second
        self._base_update(anki_note)


class ClozeNote(TwNote):
    "A cloze deletion-based note, much like Anki's built-in Cloze note type."
    model = TiddlyRememberCloze

    def __init__(self, id_: Twid, wiki: Wiki, tidref: str, text: str,
                 target_tags: Set[str], target_deck: Optional[str],
                 media: Optional[Set[TwMedia]] = None,
                 schedule: Optional[SchedulingInfo] = None) -> None:
        super().__init__(id_, wiki, tidref, target_tags, target_deck, media,
                         schedule)
        self.text = text

    def __repr__(self):
        return (f"ClozeNote(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"text={self.text!r}, target_tags={self.target_tags!r}, "
                f"target_deck={self.target_deck!r}, "
                f"schedule={self.schedule!r})")

    @classmethod
    def export_macro(cls, anki_note: Note, sched: Optional[str] = None) -> str:
        def clz_sub(text: str) -> str:
            "Replace Anki-style occlusions with TiddlyRemember-style ones."
            def repl(match):
                escaped_content = match.group(1).replace('{', r'\{').replace('}', r'\}')
                return '{' + escaped_content + '}'
            return re.sub(r"{{(c[0-9]+::.*?)}}", repl, text)

        idx = cls.model.field_index_by_name
        sched_fragment = ('\n    sched:"' + sched + '"') if sched else ""
        return (
            f"<<remembercz\n"
            f'    "{anki_note.fields[idx(ID_FIELD_NAME)]}"\n'
            f"    {munge_export_field(clz_sub(anki_note.fields[idx('Text')]))}{sched_fragment}>>" # pylint: disable=line-too-long
        )

    @classmethod
    def parse_html(cls, soup: BeautifulSoup, wiki: Wiki,
                   tiddler_name: str, warnings: List[str]) -> Set['ClozeNote']:
        notes = set()
        deck, tags = _get_deck_and_tags(soup)

        media: Set[TwMedia] = set()
        pairs = soup.find_all(class_="remembercz")
        for pair in pairs:
            pair = extract_media(media, pair, wiki, tiddler_name, warnings)
            text = clean_field_html(pair.find("span", class_="cloze-text"))
            id_raw = pair.find("div", class_="rid").get_text()
            id_ = id_raw.strip().lstrip('[').rstrip(']')
            tidref = select_tidref(pair.find("div", class_="tr-reference"),
                                   tiddler_name)
            parsed_text = ankify_clozes(text)
            sched = build_scheduling_info(pair, tiddler_name)
            notes.add(cls(id_, wiki, tidref, parsed_text, tags, deck, media,
                          sched))

        return notes

    @classmethod
    def wants_soup(cls, soup: BeautifulSoup) -> bool:
        return bool(soup.find(class_="remembercz"))

    def _fields_equal(self, anki_note: Note) -> bool:
        return self.text == anki_note['Text'] and self._base_equal(anki_note)

    def _update_fields(self, anki_note: Note) -> None:
        anki_note['Text'] = self.text
        self._base_update(anki_note)


def _get_deck_and_tags(tiddler_soup: BeautifulSoup) -> Tuple[Optional[str], Set[str]]:
    """
    Given the soup of a tiddler, extract its deck and list of tags.
    """
    deck_list = tiddler_soup.find("ul", id="anki-decks")
    if deck_list:
        first_item = deck_list.find("li")
        deck = first_item.get_text() if first_item is not None else None
    else:
        deck = None

    tag_list = tiddler_soup.find("ul", id="anki-tags")
    if tag_list:
        tags = set(i.get_text() for i in tag_list.find_all("li"))
    else:
        tags = set()

    return deck, tags


def by_name(model_name: str) -> Optional[Type[TwNote]]:
    """
    Return the TwNote class which uses the model named `model_name`.

    >>> by_name('TiddlyRemember Q&A v1')
    <class 'src.twnote.QuestionNote'>

    >>> by_name('Nonexistent Model')
    """
    for cls in TwNote.__subclasses__():
        if cls.model.name == model_name:
            return cls
    return None


def build_scheduling_info(soup: BeautifulSoup,
                          tiddler_name: str) -> Optional[SchedulingInfo]:
    """
    Given the soup of a remember* call,
    build and return an object for any scheduling information included on the call.
    """
    try:
        sched_str = soup.find("div", class_="tr-sched").get_text()
    except AttributeError:
        # backwards compatibility: no tr-sched block will be present in older versions
        return None
    if not sched_str.strip():
        return None

    try:
        d = dict((k.strip(), v.strip())
                for k, v in (i.split(':') for i in sched_str.split(';')))
        return SchedulingInfo(
            ivl=int(d['ivl']),
            due=date(year=int(d['due'][0:4]),
                     month=int(d['due'][4:6]),
                     day=int(d['due'][6:8])),
            ease=int(d['ease']),
            lapses=int(d['lapses'])
        )
    except (ValueError, IndexError) as e:
        raise ScheduleParsingError(
            f"Failed to parse scheduling info string '{sched_str}' "
            f"in tiddler '{tiddler_name}'. "
            f"Please check the 'sched' parameters of remember* calls on this tiddler."
        ) from e


def clean_field_html(soup: BeautifulSoup) -> str:
    """
    Given the raw HTML for a field, such as "question" or "answer", neaten it
    up by removing anything that doesn't belong on the Anki card, such as
    outer <p> tags and internal links, and return the string of HTML that belongs
    in the field.
    """
    replace_katex(soup)

    for elem in soup.find_all("a"):
        classes = elem.attrs.get('class', None)
        if (classes is not None
                and 'href' in elem.attrs
                and 'tc-tiddlylink-external' in classes):
            # External links lose their attributes but stay links.
            elem.attrs = {'href': elem.attrs['href']}
        else:
            # Internal links just get whacked and replaced with their plaintext.
            elem.replace_with(elem.get_text())

    return ''.join(str(i) for i in soup.contents)


def replace_katex(soup: BeautifulSoup) -> None:
    r"""
    Given the raw HTML for a field, such as "question" or "answer", remove extra crud
    associated with KaTeX markup in TiddlyWiki by replacing it in-place, and convert
    to MathJax markup surrounds that Anki will understand, i.e., $$ x $$ --> \( x \).
    """
    display_katex_fragments = soup.find_all("span", class_="katex-display")
    for k in display_katex_fragments:
        mathml = k.find("span", class_="katex-mathml")
        k.parent.replace_with(r'<span class="tw-katex-display">\[ '
                              + mathml.math.semantics.annotation.text.strip()
                              + r' \]</span>')

    inline_katex_fragments = soup.find_all("span", class_="katex")
    for k in inline_katex_fragments:
        mathml = k.find("span", class_="katex-mathml")
        k.parent.replace_with(r'<span class="tw-katex-inline">\( '
                              + mathml.math.semantics.annotation.text.strip()
                              + r' \)</span>')


def ensure_version(soup: BeautifulSoup) -> None:
    """
    Given the soup of a tiddler, which contains a version assertion,
    raise an exception if the user's TiddlyWiki plugin version is incompatible
    with her Anki plugin version.
    """
    element = soup.find("span", id="tr-version")
    if element:
        tw_plugin_version = element.get_text().strip()
    else:
        tw_plugin_version = ""

    if tw_plugin_version not in COMPATIBLE_TW_VERSIONS:
        compat_versions = ', '.join(i for i in COMPATIBLE_TW_VERSIONS if i.strip())
        raise ConfigurationError(
            f"Your Anki plugin is at version {PLUGIN_VERSION}, "
            f"but your TiddlyWiki plugin is at version {tw_plugin_version}. "
            f"This version of the Anki plugin is compatible with the following "
            f"TiddlyRemember plugin versions: {compat_versions}. "
            f"Please update your Anki and TiddlyWiki plugins to the latest version, "
            f"then try syncing again.")


def extract_media(media: Set[TwMedia], soup: BeautifulSoup, wiki: Wiki,
                  tiddler_name: str, warnings: List[str]) -> BeautifulSoup:
    """
    Extract media references from the //fields//, retrieve the associated media,
    and update the media references.

    `soup` is returned possibly modified. The `media` set is updated in-place.
    """
    for elem in soup.find_all(("img", "audio")):
        src = elem.attrs.get('src', None)
        if src is not None:
            open_src = src
            if '://' not in src and not src.startswith('data:'):
                # Try reading as a relative path if this is a file or URL wiki,
                # as this is a common way to work with _canonical_uri.
                # The resulting path is not guaranteed to exist; we'll warn the
                # user if it isn't.
                if wiki.type == WikiType.URL:
                    assert isinstance(wiki.source_path, str)  # URLs use str union type
                    open_src = (wiki.source_path
                                + ('/' if wiki.source_path[-1] != '/' else '')
                                + src)
                elif wiki.type == WikiType.FILE:
                    assert isinstance(wiki.source_path, Path)  # Paths use Path type
                    with pushd(wiki.source_path.parent):
                        open_src = Path(src).absolute().as_uri()

            try:
                with urlopen(open_src) as response:
                    medium = TwMedia(response.read(), src, warnings)
                    media.add(medium)

                    if elem.name == 'img':
                        elem.attrs['src'] = medium.filename
                    elif elem.name == 'audio':
                        elem.replace_with(f"[sound:{medium.filename}]")
            except ValueError:
                warnings.append(
                    f"Image '{src}' in tiddler '{tiddler_name}' isn't a valid URL, "
                    f"so we couldn't retrieve it and sync it into Anki."
                )
            except HTTPError as e:
                # Leave the URL so if it comes back later we can still access it.
                if e.code == 404:
                    warnings.append(
                        f"Image '{src}' in tiddler '{tiddler_name}' could not be "
                        f"retrieved at sync time: 404 Not Found.")
                elif e.code in (400, 403, 500, 502):
                    warnings.append(
                        f"Image '{src}' in tiddler '{tiddler_name}' could not be "
                        f"retrieved at sync time: HTTP {e.code} error.")
                else:
                    raise ExtractError(
                        "Unable to retrieve media files from the Internet. "
                        "Please check your network connection and review the error "
                        "below for more information if necessary.") from e
            except URLError as e:
                raise ExtractError(
                    "Unable to retrieve media files from the Internet. "
                    "Please check your network connection and review the error "
                    "below for more information if necessary.") from e
    return soup


def munge_export_field(field: str) -> str:
    """
    Common steps run on every field which is being exported to a TiddlyRemember macro.
    """
    field = re.sub(r"\[sound:(.*?)\]",
                   r'<audio controls="controls" src="\1"></audio>',
                   field)
    return tw_quote(field)


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
