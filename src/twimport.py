#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import subprocess

from bs4 import BeautifulSoup

ZK_DIR = "/home/soren/cabinet/Me/Records/zettelkasten/zk-wiki"


@dataclass
class Question:
    id_: str
    tidref: str
    question: str
    answer: str

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)


outpt = subprocess.check_output(
    ["/home/soren/cabinet/Me/Records/zettelkasten/node_modules/.bin/tiddlywiki",
    "--output",
    "/tmp/testdir",
    "--render",
    "[!is[system]type[text/vnd.tiddlywiki]]",
    "[is[tiddler]addsuffix[.html]]",
    "text/html",
    "$:/sib/macros/remember"], cwd=ZK_DIR)

results = set()
for tiddler in Path("/tmp/testdir").glob("*.html"):
    print(f"Processing {tiddler.name}...")
    with open(tiddler, 'r') as f:
        doc = f.read()

    soup = BeautifulSoup(doc, 'html.parser')
    pairs = soup.find_all("div", class_="rememberq")
    for pair in pairs:
        question = pair.find("div", class_="rquestion").p.get_text()
        answer = pair.find("div", class_="ranswer").p.get_text()
        id_ = pair.find("div", class_="rid").get_text().strip().lstrip('[').rstrip(']')
        tidref = "tiddler"
        tidref = tiddler.name[:tiddler.name.find('.html')]

        results.add(Question(id_, tidref, question, answer))

print(results)
