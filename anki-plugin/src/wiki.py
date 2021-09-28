from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Union


class WikiType(Enum):
    FOLDER = auto()
    FILE = auto()
    URL = auto()


@dataclass
class Wiki:
    name: str
    # types of file and folder use Path, type of URL uses str
    source_path: Union[Path, str]
    folderified_path: Path
    type: WikiType
