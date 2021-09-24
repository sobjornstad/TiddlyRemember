# pylint: disable=import-error
# pylint: disable=wrong-import-position
# pylint: disable=redefined-outer-name

# Must run from the project root.
import sys
sys.path.append("anki-plugin")

import datetime
import pytest
import os
from typing import Callable

from src.oops import ScheduleParsingError
from src.twnote import SchedulingInfo, QuestionNote
from src.trmodels import ID_FIELD_NAME
from src.twimport import find_notes
from src.ankisync import sync


from testutils import fn_params, col_tuple


def _sync_note_with_edits(fn_params, col_tuple, from_tiddler: str,
                          edit_callable: Callable = None) -> str:
    fn_params['filter_'] = from_tiddler
    os.chdir(col_tuple.cwd)
    notes = find_notes(**fn_params)
    assert len(notes) == 1

    if edit_callable is not None:
        note = notes.pop()
        edit_callable(note)
        notes.add(note)

    return sync(notes, col_tuple.col, 'Default')


def _get_only_note(col_tuple):
    return col_tuple.col.getNote(col_tuple.col.find_notes("")[0])


def test_import_qa(fn_params, col_tuple):
    "Test that we can import a simple question and answer into Anki."

    # Arguably it might be better for separation of concerns to create a TwNote
    # manually here instead of importing it from TiddlyWiki. For now, this is
    # easier and gives a more complete integration test, so given the limited testing
    # I currently have time to put in here, I think this is a smarter choice.
    fn_params['filter_'] = "BasicQuestionAndAnswer"
    os.chdir(col_tuple.cwd)
    notes = find_notes(**fn_params)

    # sanity check
    assert len(notes) == 1
    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 0

    userlog = sync(notes, col_tuple.col, 'Default')

    assert 'Added 1 note' in userlog
    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 1
    anki_note = col_tuple.col.getNote(anki_notes[0])
    assert anki_note.fields[0] == "What is TiddlyRemember good for?"


def test_add_with_scheduling(col_tuple):
    """
    Check that we can add a manually created note with scheduling information.
    """
    days_until_due = 4
    sched_param = {
        'due': datetime.datetime.now().date() + datetime.timedelta(days=days_until_due),
        'ivl': 5,
        'ease': 1800,
        'lapses': 1
    }
    n = QuestionNote(
        id_="20200101120000000",
        wiki_name="MyTestWiki",
        tidref="TestTiddler",
        question="Does this question get correctly scheduled?",
        answer="I hope so",
        target_tags="",
        target_deck="Default",
        schedule=SchedulingInfo(**sched_param)
    )

    sync((n,), col_tuple.col, 'Default')

    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 1
    anki_note = col_tuple.col.getNote(anki_notes[0])
    assert anki_note.fields[0] == "Does this question get correctly scheduled?"

    card = col_tuple.col.get_card(col_tuple.col.find_cards(f"nid:{anki_note.id}")[0])
    assert card.factor == sched_param['ease']
    assert card.lapses == sched_param['lapses']
    assert card.ivl == sched_param['ivl']
    assert card.due == days_until_due


def test_import_qa_with_scheduling(fn_params, col_tuple):
    "Test that we can import a question and answer into Anki with scheduling info."

    fn_params['filter_'] = "ScheduledQuestionAndAnswer"
    os.chdir(col_tuple.cwd)
    notes = find_notes(**fn_params)

    # sanity check
    assert len(notes) == 1
    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 0

    userlog = sync(notes, col_tuple.col, 'Default')

    assert 'Added 1 note' in userlog
    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 1
    anki_note = col_tuple.col.getNote(anki_notes[0])
    assert anki_note.fields[0] == "What is TiddlyRemember good for?"

    card = col_tuple.col.get_card(col_tuple.col.find_cards(f"nid:{anki_note.id}")[0])
    assert card.factor == 1800
    assert card.lapses == 1
    assert card.ivl == 5
    # year=2200 on this test card so delta will be positive for the foreseeable future
    assert card.due == (datetime.date(year=2200, month=9, day=22)
                        - datetime.datetime.now().date()).days

def test_import_invalid_scheduling(fn_params, col_tuple):
    "Test what happens when we import a note with invalid scheduling info."

    fn_params['filter_'] = "IllegalScheduledQuestionAndAnswer"
    os.chdir(col_tuple.cwd)

    with pytest.raises(ScheduleParsingError):
        find_notes(**fn_params)


def test_update_qa(fn_params, col_tuple):
    "Test that we can update a previously imported question and answer."

    # initial sync
    _sync_note_with_edits(fn_params, col_tuple, "BasicQuestionAndAnswer")

    # update
    def update(note):
        note.question = "How much wood could a woodchuck chuck?"
    userlog = _sync_note_with_edits(fn_params, col_tuple, "BasicQuestionAndAnswer",
                                    update)

    assert 'Updated 1 note' in userlog
    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 1
    anki_note = col_tuple.col.getNote(anki_notes[0])
    assert anki_note.fields[0] == "How much wood could a woodchuck chuck?"


def test_delete_qa(fn_params, col_tuple):
    "Test that we can delete a previously imported question and answer."

    _sync_note_with_edits(fn_params, col_tuple, "BasicQuestionAndAnswer")
    assert len(col_tuple.col.find_notes("")) == 1
    userlog = sync(set(), col_tuple.col, 'Default')

    assert not col_tuple.col.find_notes("")
    assert 'Removed 1 note' in userlog


def test_change_twoside_note_type(fn_params, col_tuple):
    "Test that swapping note types between 1 and 2-sided doesn't cause any errors."
    _sync_note_with_edits(fn_params, col_tuple, "BasicPair")
    used_id = _get_only_note(col_tuple)[ID_FIELD_NAME]
    def reset_id(note):
        note.id_ = used_id
    _sync_note_with_edits(fn_params, col_tuple, "BasicQuestionAndAnswer", reset_id)
    _sync_note_with_edits(fn_params, col_tuple, "BasicPair", reset_id)
