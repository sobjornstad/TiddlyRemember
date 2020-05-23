#!/usr/bin/env python3

import os
from pathlib import Path
import requests
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable, Optional, Set, Sequence

from bs4 import BeautifulSoup

from .twnote import TwNote

RENDERED_FILE_EXTENSION = "html"


def invoke_tw_command(cmd: Sequence[str], wiki_path: Optional[str],
                      description: str) -> None:
    """
    Call the TiddlyWiki node command with the provided arguments and handle errors.
    """
    try:
        proc = subprocess.run(cmd, cwd=wiki_path, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=True)
    except FileNotFoundError:
        raise Exception(
            f"The TiddlyWiki executable at '{cmd[0]}' was not found. Please set the "
            f"'tiddlywikiBinary' option in your TiddlyRemember configuration to the "
            f"path to your 'tiddlywiki' command. If you do not have TiddlyWiki on "
            f"Node.JS installed on your computer, please install it now.")
    except subprocess.CalledProcessError as proc:
        stdout = proc.stdout.decode() if proc.stdout else "(no output)"
        raise Exception(f"Failed to {description}: return code {proc.returncode}.\n"
                        f"$ {' '.join(proc.cmd)}\n\n{stdout}")


def folderify_wiki(tw_binary: str, wiki_path: str, output_directory: str) -> None:
    """
    Convert a single-file wiki into a folder wiki so we can continue working with it.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki file to convert to a folder.
    :param output_directory: Directory to place the folder wiki in.
    """
    if not os.path.exists(wiki_path):
        raise Exception(f"The wiki file '{wiki_path}' does not exist. "
                        f"Please check your TiddlyRemember configuration.")
    elif not os.path.isfile(wiki_path):
        raise Exception(f"The wiki file '{wiki_path}' is a folder. If you meant to "
                        f"use a folder wiki, set the 'type' parameter to 'folder'.")

    cmd = [tw_binary, "--load", wiki_path, "--savewikifolder", output_directory]
    invoke_tw_command(cmd, None, "folderify wiki")


def download_wiki(url: str, target_location: str) -> None:
    """
    Download a wiki from a URL to the path target_location.
    """
    r = requests.get(url)
    r.raise_for_status()
    with open(target_location, 'wb') as f:
        f.write(r.text.encode('utf-8'))


def render_wiki(tw_binary: str, wiki_path: str, output_directory: str,
                filter_: str) -> None:
    """
    Request that TiddlyWiki render the specified tiddlers as html to a
    location where we can inspect them for notes.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki folder to render.
    :param output_directory: Directory to render html files into.
    :param filter_: TiddlyWiki filter describing which tiddlers we want
                    to search for notes.
    """
    if not os.path.exists(wiki_path):
        raise Exception(f"The wiki folder '{wiki_path}' does not exist. "
                        f"Please check your TiddlyRemember configuration.")
    elif not os.path.isdir(wiki_path):
        raise Exception(f"The wiki folder '{wiki_path}' is a file. If you meant to "
                        f"use a single-file wiki, set the 'type' parameter to 'file'.")

    cmd = [
        tw_binary,
        "--output",
        output_directory,
        "--render",
        filter_,
        f"[is[tiddler]addsuffix[.{RENDERED_FILE_EXTENSION}]]",
        "text/html",
        "$:/plugins/sobjornstad/TiddlyRemember/templates/TiddlyRememberParseable"
    ]
    invoke_tw_command(cmd, wiki_path, "render wiki")


def notes_from_tiddler(tiddler: str, wiki_name: str, tiddler_name: str) -> Set[TwNote]:
    """
    Given the text of a tiddler, parse the contents and return a set
    containing all the TwNotes found within that tiddler.

    :param tiddler:      The rendered text of a tiddler as a string.
    :param wiki_name:    The name of the wiki this tiddler comes from,
                         for traceability purposes.
    :param tiddler_name: The name of the tiddler itself, for traceability purposes.
    :return: A (possibly empty) set of all the notes found in this tiddler.
    """
    soup = BeautifulSoup(tiddler, 'html.parser')
    return TwNote.notes_from_soup(soup, wiki_name, tiddler_name)


def notes_from_paths(
    paths: Sequence[Path],
    wiki_name: str,
    callback: Optional[Callable[[int, int], None]]) -> Set[TwNote]:
    """
    Given an iterable of paths, compile the notes found in all those tiddlers.

    :param paths: The paths of the tiddlers to generate notes for.
    :param wiki_name: The name/id of the wiki these notes are from.
    :param callback: Optional callable passing back progress. See :func:`find_notes`.
    :return: A set of all the notes found in the tiddler files passed.
    """
    notes = set()
    for index, tiddler in enumerate(paths, 0):
        with open(tiddler, 'r') as f:
            tid_text = f.read()
        tid_name = tiddler.name[:tiddler.name.find(f".{RENDERED_FILE_EXTENSION}")]
        notes.update(notes_from_tiddler(tid_text, wiki_name, tid_name))

        if callback is not None and not index % 50:
            callback(index+1, len(paths))

    if callback is not None:
        callback(len(paths), len(paths))
    return notes


def find_notes(
    tw_binary: str, wiki_path: str, wiki_type: str, wiki_name: str, filter_: str,
    callback: Optional[Callable[[int, int], None]] = None) -> Set[TwNote]:
    """
    Return a set of TwNotes parsed out of a TiddlyWiki.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki URL, file or folder to render.
    :param wiki_type: 'folder', 'file', or 'url'. File wikis will be rendered to
                      folders for further processing. URL wikis will first be
                      downloaded, then rendered. 'url' implies a single-file wiki.
    :param wiki_name: The name/ID the user has provided for the wiki, to be used as
                      part of the tiddler reference field.
    :param filter_:   TiddlyWiki filter describing which tiddlers
                      to search for notes.
    :param callback:  Optional callable receiving two integers, the first representing
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
        elif wiki_type == 'url':
            downloaded_file = os.path.join(tmpdir, 'wiki.html') 
            download_wiki(url=wiki_path, target_location=downloaded_file)
            wiki_folder = os.path.join(tmpdir, 'wikifolder')
            folderify_wiki(tw_binary, downloaded_file, wiki_folder)
        else:
            raise Exception(f"Invalid wiki type '{wiki_type}' -- must be "
                            f"'file', 'folder', or 'url'.")

        render_location = os.path.join(tmpdir, 'render')
        render_wiki(tw_binary, wiki_folder, render_location, filter_)
        notes = notes_from_paths(
            list(Path(render_location).glob(f"*.{RENDERED_FILE_EXTENSION}")),
            wiki_name,
            callback)

    return notes
