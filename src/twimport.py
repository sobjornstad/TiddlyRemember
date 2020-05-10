#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable, Iterable, Optional, Set, Sequence

from bs4 import BeautifulSoup

RENDERED_FILE_EXTENSION = "html"


@dataclass
class Note:
    id_: str
    tidref: str
    question: str
    answer: str

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)


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
        "$:/sib/macros/remember"]

    #TODO: Error handling
    subprocess.call(cmd, cwd=wiki_path)


def notes_from_tiddler(tiddler: str, name: str) -> Set[Note]:
    """
    Given the text of a tiddler, parse the contents and return a set
    containing all the Notes found within that tiddler.
    """
    notes = set()
    soup = BeautifulSoup(tiddler, 'html.parser')
    pairs = soup.find_all("div", class_="rememberq")
    for pair in pairs:
        question = pair.find("div", class_="rquestion").p.get_text()
        answer = pair.find("div", class_="ranswer").p.get_text()
        id_ = pair.find("div", class_="rid").get_text().strip().lstrip('[').rstrip(']')
        notes.add(Note(id_, name, question, answer))

    return notes


def notes_from_paths(
    paths: Sequence[Path],
    callback: Optional[Callable[[int, int], None]]) -> Set[Note]:
    """
    Given an iterable of paths, compile the notes found in all those
    tiddlers.

    Optionally, call a /callback/ function every 50 tiddlers, passing in the
    current tiddler number and the total number of tiddlers to be processed.
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


def find_notes(tw_binary: str, wiki_path: str, filter_: str,
               callback: Optional[Callable[[int, int], None]] = None) -> Set[Note]:
    """
    Return a set of Notes parsed out of a TiddlyWiki.

    :param tw_binary: Path to the TiddlyWiki node executable.
    :param wiki_path: Path of the wiki folder to render.
    :param filter_: TiddlyWiki filter describing which tiddlers
                    to search for notes.
    :param callback: Optional callable receiving two integers, the first representing
                     the number of tiddlers processed and the second the total number.
                     It will be called every 50 tiddlers. The first call is made at
                     tiddler 1, once the wiki has been rendered.
    """
    with TemporaryDirectory() as tmpdir:
        render_wiki(tw_binary, wiki_path, tmpdir, filter_)
        notes = notes_from_paths(
            list(Path(tmpdir).glob(f"*.{RENDERED_FILE_EXTENSION}")),
            callback)

    return notes

if __name__ == '__main__':
    notes = find_notes(
        tw_binary="/home/soren/cabinet/Me/Records/zettelkasten/node_modules/.bin/tiddlywiki",
        wiki_path="/home/soren/cabinet/Me/Records/zettelkasten/zk-wiki",
        filter_="[!is[system]type[text/vnd.tiddlywiki]]",
        callback=lambda cur, tot: print(f"{cur}/{tot}"))
    print(notes)
