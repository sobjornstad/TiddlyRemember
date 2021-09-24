class TrError(Exception):
    "General application-level error for TiddlyRemember."


class ExtractError(TrError):
    "Error that occurs while extracting notes from a TW."


class RenderingError(ExtractError):
    "A type of extract error that occurs when Node fails to render the wiki to HTML."


class ScheduleParsingError(TrError):
    """
    A type of extra error that occurs when the 'sched' string of a note
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

class UnmatchedBracesError(TrError):
    "Occurs when parsing clozes and the user has braces that don't match}."
