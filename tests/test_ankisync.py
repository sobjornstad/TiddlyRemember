# pylint: disable=import-error
# pylint: disable=wrong-import-position
# pylint: disable=redefined-outer-name

# Must run from the project root.
import sys
sys.path.append("anki-plugin")

import os

from src.twimport import find_notes
from src.ankisync import sync

from testutils import fn_params, col_tuple


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


def test_update_qa(fn_params, col_tuple):
    "Test that we can update a previously imported question and answer."

    # initial sync
    fn_params['filter_'] = "BasicQuestionAndAnswer"
    os.chdir(col_tuple.cwd)
    notes = find_notes(**fn_params)
    assert len(notes) == 1
    sync(notes, col_tuple.col, 'Default')

    # update
    change_note = notes.pop()
    change_note.question = "How much wood could a woodchuck chuck?"
    notes.add(change_note)
    userlog = sync(notes, col_tuple.col, 'Default')

    assert 'Updated 1 note' in userlog
    anki_notes = col_tuple.col.find_notes("")
    assert len(anki_notes) == 1
    anki_note = col_tuple.col.getNote(anki_notes[0])
    assert anki_note.fields[0] == "How much wood could a woodchuck chuck?"
