"""
wiki.py - objects storing wiki metadata
"""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Union


class WikiType(Enum):
    "How are we retrieving the contents of this wiki?"
    FOLDER = auto()
    FILE = auto()
    URL = auto()


@dataclass
class Wiki:
    "One TiddlyWiki source that we are syncing with."
    name: str
    # types of file and folder use Path, type of URL uses str
    source_path: Union[Path, str]
    folderified_path: Path
    type: WikiType
