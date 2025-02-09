"""
Common utility functions for tests.
"""

from collections import namedtuple
import os
import sys

from anki.collection import Collection
import pytest
import requests


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


@pytest.fixture
def file_requests_session():
    """
    Get a requests session that is capable of reading from the local filesystem.

    Thanks to https://stackoverflow.com/a/27786580/1938956 (lightly modified).
    """
    if sys.version_info.major < 3:
        from urllib import url2pathname  # pylint: disable=no-name-in-module, import-outside-toplevel
    else:
        from urllib.request import url2pathname  # pylint: disable=no-name-in-module, import-outside-toplevel

    class LocalFileAdapter(requests.adapters.BaseAdapter):
        "Protocol adapter to allow requests to GET file:// URLs."

        @staticmethod
        def _chkpath(method, path):
            """Return an HTTP status for the given filesystem path."""
            if method.lower() in ('put', 'delete'):
                return 501, "Not Implemented"
            elif method.lower() not in ('get', 'head'):
                return 405, "Method Not Allowed"
            elif os.path.isdir(path):
                return 400, "Path Not A File"
            elif not os.path.isfile(path):
                return 404, "File Not Found"
            elif not os.access(path, os.R_OK):
                return 403, "Access Denied"
            else:
                return 200, "OK"

        def send(self, req, **kwargs):  # pylint: disable=unused-argument, arguments-differ
            "Return the file specified by the given request."
            path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
            response = requests.Response()
            response.encoding = 'utf-8'

            response.status_code, response.reason = self._chkpath(req.method, path)
            if response.status_code == 200 and req.method.lower() != 'head':
                try:
                    response.raw = open(path, 'rb')
                except (OSError, IOError) as err:
                    response.status_code = 500
                    response.reason = str(err)

            if isinstance(req.url, bytes):
                response.url = req.url.decode('utf-8')
            else:
                response.url = req.url

            response.request = req
            response.connection = self

            return response

        def close(self):
            pass

    requests_session = requests.session()
    requests_session.mount('file://', LocalFileAdapter())
    return requests_session


@pytest.fixture
def mock_tiddler_deck_tags(request, monkeypatch):
    """
    Mock the _get_tiddler_deck_and_tags function to return a deck and tags other
    than the (blank) one defined in the test wiki.
    """
    def mock_get_tiddler_deck_tags(*args):  # pylint: disable=unused-argument
        return request.param['deck'], request.param['tags']
    monkeypatch.setattr(
        "src.twnote._get_tiddler_deck_and_tags",
        mock_get_tiddler_deck_tags
    )
