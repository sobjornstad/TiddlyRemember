"""
Common utility functions for tests.
"""

from collections import namedtuple
import os

from anki import Collection
import pytest

TIDDLYWIKI_BINARY = "tiddlywiki"
TestCollection = namedtuple('TestCollection', ['col', 'cwd'])


@pytest.fixture
def fn_params():
    return {
        'tw_binary': TIDDLYWIKI_BINARY,
        'wiki_path': "tests/wiki/",
        'wiki_type': "folder",
        'wiki_name': "TestWiki",
        'callback': None
    }


@pytest.fixture
def col_tuple(tmpdir):
    """
    Get a test Anki collection.

    Anki irritatingly changes the working directory to the media directory, so
    also return our old working directory.
    """
    old_cwd = os.getcwd()
    my_col = Collection(tmpdir / "collection.anki2")
    col_obj = TestCollection(my_col, old_cwd)
    try:
        yield col_obj
    finally:
        my_col.close()
