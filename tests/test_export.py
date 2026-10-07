"""
test_export - test the export of TiddlyWiki macros from Anki
"""

# pylint: disable=import-error
# pylint: disable=wrong-import-position
# pylint: disable=redefined-outer-name

# Must run from the project root.
import sys
sys.path.append("anki-plugin")

import dataclasses
import os
from textwrap import dedent

import pytest

from anki.collection import (
    CardIdsLimit, DeckIdLimit, ExportLimit, NoteIdsLimit
)
from aqt.import_export.exporting import ExportOptions

from src.ankisync import sync
from src.macro_exporter import export_macro_file, note_ids_for_limit
from src.twimport import find_notes

from testutils import col_tuple, fn_params


def export_options(out_path: str, include_scheduling: bool) -> ExportOptions:
    """
    Build the ExportOptions that Anki's export dialog would hand our exporter.

    ExportOptions has gained fields over the years and they're all mandatory,
    so fill in only the ones the installed version of Anki actually has.
    """
    wanted = {
        'out_path': out_path,
        'include_scheduling': include_scheduling,
        'include_deck_configs': False,
        'include_media': False,
        'include_tags': False,
        'include_html': True,
        'include_deck': False,
        'include_notetype': False,
        'include_guid': False,
        'legacy_support': False,
        'limit': None,
    }
    fields = dataclasses.fields(ExportOptions)
    required = {f.name for f in fields
                if f.default is dataclasses.MISSING
                and f.default_factory is dataclasses.MISSING}
    assert wanted.keys() >= required, \
        f"ExportOptions has new mandatory fields: {required - wanted.keys()}"
    available = {f.name for f in fields}
    return ExportOptions(**{k: v for k, v in wanted.items() if k in available})


@pytest.mark.parametrize(
    ("test_case_name", "include_scheduling", "output"),
    [
        # Basic types
        ("BasicQuestionAndAnswer", False, """
            <<rememberq
                "20200925171619043"
                "What is TiddlyRemember good for?"
                "Remembering things that you put in your TiddlyWiki.">>
            """),
        ("BasicPair", False, """
            <<rememberp
                "20200925223930460"
                "One"
                "1">>
            """),
        ("EscapedCloze", False, r"""
            <<remembercz
                "20210925133938745"
                "In LaTeX, we create fractions with {c1::<code>\frac\{numerator\}\{denominator\}</code>}.">>
            """),

        # Hard references and other options aren't preserved.
        ("HardrefQa", False, """
            <<rememberq
                "20200925183527082"
                "Do hard references work in TiddlyRemember?"
                "I don't know, you tell me!">>
            """),

        # Nothing special happens to media references, and the Anki name is preserved.
        # So if you want the images, you can drag and drop them out of
        # the media folder into a wiki to import them and everything should work.
        ("InternalDogImageTest", False, """
            <<rememberq
                "20210928004052765"
                "What does a dog look like?"
                '<img class="tc-image-loading" src="tr-f53cec5dc23d10d91500c50d79ccb4e73df697f64fc2cd93a1b2fcf2698775c5.jpg" width="300"/>'>>
            """),
        ("AudioTest", False, '''
            <<rememberq
                "20210928205233830"
                """What's this audio file?<br/><audio controls="controls" src="tr-07d11170fe30596ca17307682d2745e09862a8dcdf90c76fa90b70d381eb4973.mp3"></audio>"""
                "A <em>test</em> audio file.">>
            '''),

        # Scheduling can be included.
        ("ScheduledQuestionAndAnswer", True, '''
            <<rememberq
                "20200925171619043"
                "What is TiddlyRemember good for?"
                "Remembering things that you put in your TiddlyWiki."
                sched:"due:220009221200000;ivl:5;ease:1800;lapses:1">>
            '''),
        # But it isn't included even if it exists if you say not to.
        ("ScheduledQuestionAndAnswer", False, '''
            <<rememberq
                "20200925171619043"
                "What is TiddlyRemember good for?"
                "Remembering things that you put in your TiddlyWiki.">>
            '''),
        # And if you say to but it's a new card, there won't be any.
        ("BasicQuestionAndAnswer", True, """
            <<rememberq
                "20200925171619043"
                "What is TiddlyRemember good for?"
                "Remembering things that you put in your TiddlyWiki.">>
            """),
    ]
)
def test_export(fn_params, col_tuple, tmp_path,
                test_case_name, include_scheduling, output):
    "Check that we can sync an item into Anki and then export it as a TiddlyWiki macro."
    fn_params['filter_'] = test_case_name
    os.chdir(col_tuple.cwd)
    notes = find_notes(**fn_params)
    sync(notes, col_tuple.col, "Default")

    out_path = str(tmp_path / "output.tid")
    count = export_macro_file(
        col_tuple.col,
        export_options(out_path=out_path, include_scheduling=include_scheduling))
    with open(out_path, "r") as f:  # pylint: disable=unspecified-encoding
        macros = f.read()
    assert macros == dedent(output).strip()
    assert count == 1


@pytest.mark.parametrize("limit_type", ["all", "deck", "notes", "cards"])
def test_export_limits(fn_params, col_tuple, tmp_path, limit_type):
    """
    Whichever way the export dialog describes the notes to export, we find them.
    """
    fn_params['filter_'] = "BasicQuestionAndAnswer"
    os.chdir(col_tuple.cwd)
    col = col_tuple.col
    sync(find_notes(**fn_params), col, "Default")

    nids = col.find_notes("")
    assert len(nids) == 1
    limit: ExportLimit
    if limit_type == "all":
        limit = None
    elif limit_type == "deck":
        limit = DeckIdLimit(col.decks.id_for_name("Default"))
    elif limit_type == "notes":
        limit = NoteIdsLimit(nids)
    else:
        limit = CardIdsLimit(col.find_cards(""))

    options = export_options(out_path=str(tmp_path / "output.tid"),
                             include_scheduling=False)
    options.limit = limit
    assert export_macro_file(col, options) == 1
    assert note_ids_for_limit(col, limit) == list(nids)


def test_export_skips_foreign_note_types(col_tuple, tmp_path):
    "Notes that aren't in TiddlyRemember format are left out of the export."
    col = col_tuple.col
    note = col.new_note(col.models.by_name("Basic"))
    note['Front'] = "Not a TiddlyRemember note"
    col.add_note(note, col.decks.id_for_name("Default"))

    out_path = str(tmp_path / "output.tid")
    count = export_macro_file(
        col, export_options(out_path=out_path, include_scheduling=False))
    assert count == 0
    with open(out_path, "r") as f:  # pylint: disable=unspecified-encoding
        assert f.read() == ""
