#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Set

from bs4 import BeautifulSoup

ZK_DIR = "/home/soren/cabinet/Me/Records/zettelkasten/zk-wiki"


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
        "[is[tiddler]addsuffix[.html]]",
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

render_wiki(
    "/home/soren/cabinet/Me/Records/zettelkasten/node_modules/.bin/tiddlywiki",
    ZK_DIR,
    "/tmp/testdir",
    "[!is[system]type[text/vnd.tiddlywiki]]")

notes = set()
for tiddler in Path("/tmp/testdir").glob("*.html"):
    with open(tiddler, 'r') as f:
        tid_text = f.read()
    tid_name = tiddler.name[:tiddler.name.find('.html')]
    print(f"Processing {tid_name}...")
    notes.update(notes_from_tiddler(tid_text, tid_name))

print(notes)
