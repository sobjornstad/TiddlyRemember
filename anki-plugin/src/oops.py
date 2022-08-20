"""
oops.py - TiddlyRemember exception definitions
"""

class TrError(Exception):
    "General application-level error for TiddlyRemember."


class ExtractError(TrError):
    "Error that occurs while extracting notes from a TW."


class RenderingError(ExtractError):
    "A type of extract error that occurs when Node fails to render the wiki to HTML."


class TiddlerParsingError(ExtractError):
    """
    A type of extract error that occurs when something generic goes wrong while
    parsing the text of a tiddler.
    """

    def __init__(self, tiddler_name: str) -> None:
        super().__init__()
        self.tiddler_name = tiddler_name

    def __str__(self) -> str:
        return f"Could not parse tiddler {self.tiddler_name}."

class ScheduleParsingError(ExtractError):
    """
    A type of extract error that occurs when the 'sched' string of a note
    is in an invalid format.
    """

class ConfigurationError(ExtractError):
    """
    A type of extract error that occurs when the user set invalid configuration
    parameters for the render.
    """


class AnkiStateError(TrError):
    """
    Error that occurs when note types or other objects in Anki have been
    manually modified in a way that makes them incompatible with TiddlyRemember.
    """
