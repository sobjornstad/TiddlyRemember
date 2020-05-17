#!/usr/bin/env python3

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable, Optional, Set, Sequence

from bs4 import BeautifulSoup

from .twnote import TwNote, QuestionNote

RENDERED_FILE_EXTENSION = "html"


def folderify_wiki(tw_binary: str, wiki_path: str, output_directory: str) -> None:
    """
    Convert a single-file wiki into a folder wiki so we can continue working with it.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki file to convert to a folder.
    :param output_directory: Directory to place the folder wiki in.
    """
    cmd = [tw_binary, "--load", wiki_path, "--savewikifolder", output_directory]
    #TODO: Error handling
    subprocess.call(cmd)


def render_wiki(tw_binary: str, wiki_path: str, output_directory: str, filter_: str) -> None:
    """
    Request that TiddlyWiki render the specified tiddlers as html to a
    location where we can inspect them for notes.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki folder to render.
    :param output_directory: Directory to render html files into.
    :param filter_: TiddlyWiki filter describing which tiddlers we want
                    to search for notes.
    """
    cmd = [
        tw_binary,
        "--output",
        output_directory,
        "--render",
        filter_,
        f"[is[tiddler]addsuffix[.{RENDERED_FILE_EXTENSION}]]",
        "text/html",
        "$:/plugins/sobjornstad/tiddlyremember/templates/TiddlyRememberParseable"
    ]

    #TODO: Error handling
    subprocess.call(cmd, cwd=wiki_path)


def notes_from_tiddler(tiddler: str, name: str) -> Set[TwNote]:
    """
    Given the text of a tiddler, parse the contents and return a set
    containing all the TwNotes found within that tiddler.

    :param tiddler: The rendered text of a tiddler as a string.
    :param name: The name of the tiddler, for traceability purposes.
    :return: A (possibly empty) set of all the notes found in this tiddler.
    """
    soup = BeautifulSoup(tiddler, 'html.parser')
    return TwNote.notes_from_soup(soup, name)


def notes_from_paths(
    paths: Sequence[Path],
    callback: Optional[Callable[[int, int], None]]) -> Set[TwNote]:
    """
    Given an iterable of paths, compile the notes found in all those tiddlers.

    :param paths:
    :param callback: Optional callable passing back progress. See :func:`find_notes`.
    :return: A set of all the notes found in the tiddler files passed.
    """
    notes = set()
    for index, tiddler in enumerate(paths, 0):
        with open(tiddler, 'r') as f:
            tid_text = f.read()
        tid_name = tiddler.name[:tiddler.name.find(f".{RENDERED_FILE_EXTENSION}")]
        notes.update(notes_from_tiddler(tid_text, tid_name))

        if callback is not None and not index % 50:
            callback(index+1, len(paths))

    if callback is not None:
        callback(len(paths), len(paths))
    return notes


def find_notes(
    tw_binary: str, wiki_path: str, wiki_type: str, filter_: str,
    callback: Optional[Callable[[int, int], None]] = None) -> Set[TwNote]:
    """
    Return a set of TwNotes parsed out of a TiddlyWiki.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki folder to render.
    :param wiki_type: 'folder' or 'file'. File wikis will be rendered to folders
                      for further processing.
    :param filter_: TiddlyWiki filter describing which tiddlers
                    to search for notes.
    :param callback: Optional callable receiving two integers, the first representing
                     the number of tiddlers processed and the second the total number.
                     It will be called every 50 tiddlers. The first call is made at
                     tiddler 1, once the wiki has been rendered.
    """
    with TemporaryDirectory() as tmpdir:
        if wiki_type == 'file':
            wiki_folder = os.path.join(tmpdir, 'wikifolder')
            folderify_wiki(tw_binary, wiki_path, wiki_folder)
        elif wiki_type == 'folder':
            wiki_folder = wiki_path
        else:
            raise Exception(
                "Invalid wiki type {wiki_type} -- must be 'file' or 'folder'.")

        render_location = os.path.join(tmpdir, 'render')
        render_wiki(tw_binary, wiki_folder, render_location, filter_)
        notes = notes_from_paths(
            list(Path(render_location).glob(f"*.{RENDERED_FILE_EXTENSION}")),
            callback)

    return notes
