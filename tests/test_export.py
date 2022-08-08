"""
test_export - test the export of TiddlyWiki macros from Anki
"""

# pylint: disable=import-error
# pylint: disable=wrong-import-position
# pylint: disable=redefined-outer-name

# Must run from the project root.
import sys
sys.path.append("anki-plugin")

import os
from textwrap import dedent

import pytest

from src.ankisync import sync
from src.macro_exporter import TiddlyRememberMacroExporter
from src.twimport import find_notes

from testutils import col_tuple, fn_params


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

    exp = TiddlyRememberMacroExporter(col_tuple.col)
    if include_scheduling:
        exp.includeSched = True
    exp.exportInto(tmp_path / "output.txt")
    with open(tmp_path / "output.txt", "r") as f:  # pylint: disable=unspecified-encoding
        macros = f.read()
    assert macros == dedent(output).strip()
