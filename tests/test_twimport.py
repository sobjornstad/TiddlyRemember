"""
test_twimport - test the creation of TwNote objects from a TiddlyWiki
"""

# pylint: disable=import-error
# pylint: disable=wrong-import-position
# pylint: disable=redefined-outer-name

# Must run from the project root.
import sys
sys.path.append("anki-plugin")

import os

import pytest

from src.clozeparse import UnmatchedBracesError
from src.twimport import find_notes
from src.twnote import TwNote, QuestionNote, ClozeNote, PairNote

from testutils import fn_params  # pylint: disable=unused-import


### Integration tests of basic functionality ###
def test_question_import(fn_params):
    "The 'BasicQuestionAndAnswer' note imports as expected."

    print(os.getcwd())
    fn_params['filter_'] = "BasicQuestionAndAnswer"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, TwNote)
    assert isinstance(note, QuestionNote)

    assert note.id_ == '20200925171619043'
    assert note.tidref == 'BasicQuestionAndAnswer'
    assert note.question == 'What is TiddlyRemember good for?'
    assert note.answer == 'Remembering things that you put in your TiddlyWiki.'
    assert note.target_tags == set()
    assert note.target_deck is None


def test_cloze_import(fn_params):
    "The 'BasicQuestionAndAnswer' note imports as expected."
    fn_params['filter_'] = "BasicCloze"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, TwNote)
    assert isinstance(note, ClozeNote)

    assert note.id_ == '20200925171645079'
    assert note.tidref == 'BasicCloze'
    assert note.text == ('TiddlyRemember is good for '
                         '{{c1::remembering things that you put in your TiddlyWiki}}.')
    assert note.target_tags == set()
    assert note.target_deck is None


def test_pair_import(fn_params):
    "The 'BasicPair' note imports as expected."
    fn_params['filter_'] = "BasicPair"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, TwNote)
    assert isinstance(note, PairNote)

    assert note.id_ == '20200925223930460'
    assert note.tidref == "BasicPair"
    assert note.first == "One"
    assert note.second == "1"
    assert note.target_tags == set()
    assert note.target_deck is None


def test_hardref(fn_params):
    """
    Although the note appears in 2 tiddlers, only one TwNote will be generated
    because it has been hard-referenced.
    """
    fn_params['filter_'] = "[tag[HardrefTest]]"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, QuestionNote)
    assert note.id_ == "20200925183527082"
    assert note.tidref == "HardrefQaTarget"
    assert note.question == "Do hard references work in TiddlyRemember?"


def test_formatting(fn_params):
    "Check that basic HTML formatting comes across into TwNotes."
    fn_params['filter_'] = "FormattingTest"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, ClozeNote)
    assert note.id_ == "20200926152545054"
    assert '<strong>' in note.text
    assert '<em>' in note.text
    assert '<strike>' in note.text


def test_link(fn_params):
    "Check that internal links are removed and external links comes across."
    fn_params['filter_'] = "LinkTest"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert note.id_ == "20200926154719339"
    assert note.question == 'How do you get to Google?'
    assert note.answer == \
        'Browse to <a href="https://google.com">https://google.com</a>.'


def test_recursive_link(fn_params):
    "Check that links are still cleaned up when inside another HTML element."

    fn_params['filter_'] = "RecursiveLinkTest"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert note.id_ == "20200926154719339"
    assert note.question == 'How do you get <strong>to Google</strong>?'
    assert note.answer == \
        ('Browse <span style="color: orange;">to '
         '<a href="https://google.com">https://google.com</a></span>.')


def test_external_image(fn_params):
    "Check that image references come across into TwNotes, including sizing."
    fn_params['filter_'] = "ExternalCatImageTest"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, QuestionNote)
    assert note.id_ == "20200926152139943"
    assert '<img src="https://upload.wikimedia.org' in note.answer
    assert 'width="400"' in note.answer


def test_file_import(fn_params):
    """
    Check that the file-to-folder conversion works.

    Note that the file wiki may not always have the latest copy of
    TiddlyRemember. If this test starts failing, an outdated plugin version
    should be the first thing you check for.
    """
    fn_params['filter_'] = "TiddlyRememberTest"
    fn_params['wiki_path'] = "tests/file_wiki.html"
    fn_params['wiki_type'] = "file"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()
    assert note.id_ == "20200925190437552"


def test_url_import(fn_params):
    """
    Check that the URL-to-folder conversion works.

    Note that the TiddlyRemember docs may not always have the latest copy of
    TiddlyRemember (e.g., during development, it will be one version behind).
    If this test starts failing, that should be the first thing you check.
    """
    fn_params['filter_'] = "TiddlyRemember"
    fn_params['wiki_path'] = "https://sobjornstad.github.io/TiddlyRemember/"
    fn_params['wiki_type'] = "url"
    notes = find_notes(**fn_params)
    assert notes  # don't want to make dependent on the summarized note options


def test_tiddlyremember_variable(fn_params):
    """
    Check that the variable "tr-rendering" is set to "yes" when TiddlyRemember
    is working. This will allow custom templates to be written to render or not
    render certain things. For instance, some UI elements won't work correctly
    when there is no browser, so they shouldn't appear.
    """
    fn_params['filter_'] = "TrVariableTest"
    notes = find_notes(**fn_params)
    assert len(notes) == 1
    note = notes.pop()
    assert note.answer == "yes"


### Regression tests ###
# Tests arising out of bug reports or other broken behavior.

def test_nonascii(fn_params):
    """
    Reports: non-ASCII question text or tiddler names variously broken on some
    platforms.
    """
    fn_params['filter_'] = "[field:reference-name[NonAsciiQuestionText]]"
    notes = find_notes(**fn_params)

    assert len(notes) == 1
    note = notes.pop()

    assert isinstance(note, QuestionNote)
    assert note.id_ == "20200923152852640"
    assert note.question == "What 'élan vital' means?"
    assert note.tidref == "NonAsciiQuestionTéxt😀"


def test_inlinecloze(fn_params):
    """
    Report: Inline cloze with no other block cloze in the tiddler
    not recognized at all.
    """
    fn_params['filter_'] = "MultipleInlineCloze"
    notes = find_notes(**fn_params)

    assert len(notes) == 1


def test_doubleclosingbrace(fn_params):
    """
    Report: "Single '}' encountered in format string" error
    prevents syncing.

    https://github.com/sobjornstad/TiddlyRemember/issues/29
    """
    fn_params['filter_'] = "BadClosingBraceCloze"
    with pytest.raises(UnmatchedBracesError):
        find_notes(**fn_params)
