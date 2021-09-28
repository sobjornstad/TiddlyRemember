"""
twimport.py - obtain and render TiddlyWikis and create TiddlyWiki note objects from them

This module's public interface is find_notes(), which, given information
about a wiki, returns a set of TwNotes that it found in this wiki.
"""
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable, List, Optional, Set, Sequence
import urllib

from bs4 import BeautifulSoup
import requests

from .oops import RenderingError, ConfigurationError
from .twnote import TwNote, ensure_version
from .util import nowin_startupinfo
from .wiki import Wiki, WikiType

RENDERED_FILE_EXTENSION = "html"


def _download_wiki(url: str, target_location: str,
                   requests_session: Optional[requests.Session] = None) -> None:
    """
    Download a wiki from a URL to the path target_location.
    """
    if requests_session is None:
        requests_session = requests.session()

    r = requests_session.get(url)
    r.raise_for_status()
    with open(target_location, 'wb') as f:
        f.write(r.text.encode(r.encoding))


def _folderify_wiki(tw_binary: str, wiki_path: str, output_directory: str,
                    password: str = "") -> None:
    """
    Convert a single-file wiki into a folder wiki so we can continue working with it.

    :param tw_binary:        Path to the TiddlyWiki node executable.
    :param wiki_path:        Path of the wiki file to convert to a folder.
    :param output_directory: Directory to place the folder wiki in.
    :param password:         Password with which to decrypt the wiki, if one is needed.
    """
    if not os.path.exists(wiki_path):
        raise ConfigurationError(
            f"The wiki file '{wiki_path}' does not exist. "
            f"Please check your TiddlyRemember configuration.")
    elif not os.path.isfile(wiki_path):
        raise ConfigurationError(
            f"The wiki file '{wiki_path}' is a folder. If you meant to "
            f"use a folder wiki, set the 'type' parameter to 'folder'.")

    cmd = [tw_binary]
    if password:
        cmd.extend(("--password", password))
    cmd.extend(("--load", wiki_path, "--savewikifolder", output_directory))
    _invoke_tw_command(cmd, None, "folderify wiki")


def _invoke_tw_command(cmd: Sequence[str], wiki_path: Optional[str],
                       description: str) -> None:
    """
    Call the TiddlyWiki node command with the provided arguments and handle errors.
    """
    try:
        proc = subprocess.run(cmd, cwd=wiki_path, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=True,
                              startupinfo=nowin_startupinfo())
    except FileNotFoundError as e:
        raise ConfigurationError(
            f"The TiddlyWiki executable at '{cmd[0]}' was not found. Please set the "
            f"'tiddlywikiBinary' option in your TiddlyRemember configuration to the "
            f"path to your 'tiddlywiki' command. If you do not have TiddlyWiki on "
            f"Node.JS installed on your computer, please install it now.") from e
    except subprocess.CalledProcessError as proc:
        stdout = proc.stdout.decode() if proc.stdout else "(no output)"
        if "No tiddlers found in file" in stdout:
            extra = ("(If this wiki is encrypted, "
                     "did you forget to give the password?)\n")
        raise RenderingError(
            f"Failed to {description}: return code {proc.returncode}.\n{extra}"
            f"$ {' '.join(proc.cmd)}\n\n{stdout}") from proc


def _notes_from_paths(
    paths: Sequence[Path],
    wiki: Wiki,
    callback: Optional[Callable[[int, int], None]],
    warnings: List[str]) -> Set[TwNote]:
    """
    Given an iterable of paths, compile the notes found in all those tiddlers.

    :param paths: The paths of the tiddlers to generate notes for.
    :param wiki:  Details on the wiki these notes come from.
    :param callback: Optional callable passing back progress. See :func:`find_notes`.
    :param warnings: List to add warnings of any non-critical conditions to.
    :return: A set of all the notes found in the tiddler files passed.
    """
    notes = set()
    for index, tiddler in enumerate(paths, 0):
        with open(tiddler, 'rb') as f:
            tid_text = f.read().decode()
        tid_name = urllib.parse.unquote(
            tiddler.name[:tiddler.name.find(f".{RENDERED_FILE_EXTENSION}")])
        notes.update(_notes_from_tiddler(tid_text, wiki, tid_name, warnings))

        if callback is not None and not index % 50:
            callback(index+1, len(paths))

    if callback is not None:
        callback(len(paths), len(paths))
    return notes


def _notes_from_tiddler(tiddler: str, wiki: Wiki, tiddler_name: str,
                        warnings: List[str]) -> Set[TwNote]:
    """
    Given the text of a tiddler, parse the contents and return a set
    containing all the TwNotes found within that tiddler.

    :param tiddler:      The rendered text of a tiddler as a string.
    :param wiki:         The wiki this tiddler comes from, for traceability purposes.
    :param tiddler_name: The name of the tiddler itself, for traceability purposes.
    :param warnings:     A list to add warnings of any non-critical issues to.
    :return: A (possibly empty) set of all the notes found in this tiddler.
    """
    soup = BeautifulSoup(tiddler, 'html.parser')
    ensure_version(soup)
    return TwNote.notes_from_soup(soup, wiki, tiddler_name, warnings)


def _render_wiki(tw_binary: str, wiki_path: str, output_directory: str,
                 filter_: str) -> None:
    """
    Request that TiddlyWiki render the specified tiddlers as HTML to a
    location where we can inspect them for notes.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki folder to render.
    :param output_directory: Directory to render html files into.
    :param filter_: TiddlyWiki filter describing which tiddlers we want
                    to search for notes.

    Raises:
        ConfigurationError - if something is wrong with the TR configuration
            or the Node install
        RenderingError - if Node fails to render the wiki for some unexplained reason
            (nonzero exit status)
    """
    if not os.path.exists(wiki_path):
        raise ConfigurationError(
            f"The wiki folder '{wiki_path}' does not exist. "
            f"Please check your TiddlyRemember configuration.")
    elif not os.path.isdir(wiki_path):
        raise ConfigurationError(
            f"The wiki folder '{wiki_path}' is a file. If you meant to "
            f"use a single-file wiki, set the 'type' parameter to 'file'.")

    cmd = [
        tw_binary,
        "--verbose",
        "--output",
        output_directory,
        "--render",
        filter_,
        f"[encodeuricomponent[]addsuffix[.{RENDERED_FILE_EXTENSION}]]",
        "text/html",
        "$:/plugins/sobjornstad/TiddlyRemember/templates/TiddlyRememberParseable"
    ]
    _invoke_tw_command(cmd, wiki_path, "render wiki")


def find_notes(
    tw_binary: str, wiki_path: str, wiki_type: str, wiki_name: str, filter_: str,
    password: str = "",
    requests_session: Optional[requests.Session] = None,
    callback: Optional[Callable[[int, int], None]] = None,
    warnings: Optional[List[str]] = None) -> Set[TwNote]:
    """
    Return a tuple of TwNotes parsed out of a TiddlyWiki.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki URL, file or folder to render.
    :param wiki_type: 'folder', 'file', or 'url'. File wikis will be rendered to
                      folders for further processing. URL wikis will first be
                      downloaded, then rendered. 'url' implies a single-file wiki.
    :param wiki_name: The name/ID the user has provided for the wiki, to be used as
                      part of the tiddler reference field.
    :param filter_:   TiddlyWiki filter describing which tiddlers
                      to search for notes.
    :param password:  If specified, a password needed to decrypt the wiki.
                      Only valid with file and URL wikis.
    :param requests_session: If specified, a session to be used to fetch the wiki from
                      the provided URL. Ignored unless wiki_type is 'url'. If
                      specified, one will be created with the default options.
    :param callback:  Optional callable receiving two integers, the first representing
                      the number of tiddlers processed and the second the total number.
                      It will be called every 50 tiddlers. The first call is made at
                      tiddler 1, once the wiki has been rendered.
    :param warnings:  Optional list which will have lines appended to it for any
                      non-critical issues that arise during the sync.

    Be aware that more than one TwNote can be returned for a given invocation
    of <<remember*>> in TiddlyWiki. This is because transclusions can result
    in the same rendered HTML appearing in multiple places.
    """
    if warnings is None:
        warnings = []

    with TemporaryDirectory() as tmpdir:
        try:
            if wiki_type == 'file':
                wiki_folder = os.path.join(tmpdir, 'wikifolder')
                _folderify_wiki(tw_binary, wiki_path, wiki_folder, password)
                wiki = Wiki(wiki_name, Path(wiki_path), Path(wiki_folder),
                            WikiType.FILE)

            elif wiki_type == 'folder':
                wiki_folder = wiki_path
                wiki = Wiki(wiki_name, Path(wiki_path), Path(wiki_path),
                            WikiType.FOLDER)

            elif wiki_type == 'url':
                downloaded_file = os.path.join(tmpdir, 'wiki.html')
                _download_wiki(url=wiki_path, target_location=downloaded_file,
                               requests_session=requests_session)
                wiki_folder = os.path.join(tmpdir, 'wikifolder')
                _folderify_wiki(tw_binary, downloaded_file, wiki_folder, password)
                wiki = Wiki(wiki_name, wiki_path, Path(wiki_folder), WikiType.URL)

            else:
                raise Exception(f"Invalid wiki type '{wiki_type}' -- must be "
                                f"'file', 'folder', or 'url'.")
        except ConfigurationError as e:
            # Add a little more context so it's clear where to look for the problem.
            raise ConfigurationError(
                f"There is a problem with the configuration for the wiki "
                f"'{wiki_name}': {str(e)}"
            ) from e

        render_location = os.path.join(tmpdir, 'render')
        _render_wiki(tw_binary, wiki_folder, render_location, filter_)
        notes = _notes_from_paths(
            list(Path(render_location).glob(f"*.{RENDERED_FILE_EXTENSION}")),
            wiki,
            callback,
            warnings)

    return notes
