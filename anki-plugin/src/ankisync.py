from typing import Any, Dict, NewType, Set, cast

from anki.notes import Note

from . import trmodels
from .twnote import TwNote
from .util import pluralize, Twid


def update_deck(tw_note: TwNote, anki_note: Note, mw: Any, default_deck: str) -> None:
    """
    Given a note already in Anki's database, move its cards into an
    appropriate deck if they aren't already there. All cards must go to the
    same deck for the time being -- although this is currently irrelevant
    since we don't support any note types with multiple cards!

    The note must be flushed to Anki's database for this to work correctly.
    """
    # Confusingly, mw.col.decks.id returns the ID of an existing deck, and
    # creates it if it doesn't exist. This happens to be exactly what we want.
    deck_name = tw_note.target_deck or default_deck
    new_did = mw.col.decks.id(deck_name)
    for card in anki_note.cards():
        if card.did != new_did:
            card.did = new_did
            card.flush()


def sync(tw_notes: Set[TwNote], mw: Any, conf: Any) -> str:
    """
    Compare TiddlyWiki notes with the notes currently in our Anki collection
    and add, edit, and remove notes as needed to get Anki in sync with the
    TiddlyWiki notes.

    :param twnotes: Set of TwNotes extracted from a TiddlyWiki.
    :param mw: The Anki main-window object.
    :return: A log string to pass back to the user, describing the results.

    .. warning::
        This is a unidirectional update. Any changes to notes made directly
        in Anki WILL BE LOST when the sync is run.

    The sync keys on unique IDs, which are generated by the TiddlyWiki
    plugin when you add macro calls and default to the current UTC time
    in YYYYMMDDhhmmssxxx format (xxx being milliseconds). Provided the ID
    is maintained, integrity is retained when the macro is edited and
    moved around to different tiddlers. Altering the ID in either Anki or
    TiddlyWiki will break the connection and likely cause a duplicate
    note (or, worse, an overwritten note if you reuse an existing ID).

    Be aware that deleting a note from TiddlyWiki will permanently delete
    it from Anki.
    """
    extracted_notes: Set[TwNote] = tw_notes
    extracted_twids: Set[Twid] = set(n.id_ for n in extracted_notes)
    extracted_notes_map: Dict[Twid, TwNote] = {n.id_: n for n in extracted_notes}
    model_name = trmodels.TiddlyRememberQuestionAnswer.name # pylint: disable=no-member

    anki_notes: Set[Note] = set(mw.col.getNote(nid)
                                for nid in mw.col.find_notes(f'"note:{model_name}"'))
    anki_twids: Set[Twid] = set(cast(Twid, n.fields[2]) for n in anki_notes)
    anki_notes_map: Dict[Twid, Note] = {cast(Twid, n.fields[2]): n for n in anki_notes}

    adds = extracted_twids.difference(anki_twids)
    edits = extracted_twids.intersection(anki_twids)
    removes = anki_twids.difference(extracted_twids)

    userlog = []

    for note_id in adds:
        tw_note = extracted_notes_map[note_id]
        n = Note(mw.col, mw.col.models.byName(model_name))
        n.model()['did'] = mw.col.decks.id(tw_note.target_deck     # type: ignore
                                           or conf['defaultDeck'])
        tw_note.update_fields(n)
        mw.col.addNote(n)
    userlog.append(f"Added {len(adds)} {pluralize('note', len(adds))}.")

    edit_count = 0
    for note_id in edits:
        anki_note = anki_notes_map[note_id]
        tw_note = extracted_notes_map[note_id]
        if not tw_note.fields_equal(anki_note):
            tw_note.update_fields(anki_note)
            anki_note.flush()
            edit_count += 1
        update_deck(tw_note, anki_note, mw, conf['defaultDeck'])
    userlog.append(f"Updated {edit_count} {pluralize('note', edit_count)}.")

    mw.col.remNotes(anki_notes_map[twid].id for twid in removes)
    userlog.append(f"Removed {len(removes)} {pluralize('note', len(removes))}.")

    return '\n'.join(userlog)
