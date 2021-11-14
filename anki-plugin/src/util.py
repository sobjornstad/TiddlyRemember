"""
util.py - general-purpose functions and definitions used by multiple modules
"""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
from typing import Iterator, NewType, Optional, Sequence


Twid = NewType('Twid', str)

DEFAULT_FILTER = '[type[text/vnd.tiddlywiki]] [type[]] +[!is[system]]'
PLUGIN_VERSION = "1.3.1"
COMPATIBLE_TW_VERSIONS = ["", "1.2.2", "1.2.3", "1.3.0", "1.3.1"]


def pluralize(sg: str, n: int, pl: str = None) -> str:
    """
    Return a string in one of two forms, depending on whether /n/ is 1.

    For convenience when working with English text, the plural form may be
    left blank if it consists of the singular form plus 's'.

    >>> pluralize("Soren", 2)
    'Sorens'

    >>> pluralize("potato", 1, "potatoes")
    'potato'

    >>> pluralize("potato", 6, "potatoes")
    'potatoes'

    >>> pluralize("potato", 0, "potatoes")
    'potatoes'
    """
    if n == 1:
        return sg
    else:
        if pl is None:
            pl = sg + 's'
        return pl


@contextmanager
def pushd(path: Path) -> Iterator[None]:
    "Change directory into a given path for the duration of the context."
    old_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def nowin_startupinfo() -> Optional['subprocess.STARTUPINFO']:  # type: ignore
    """
    If running on Windows, return a STARTUPINFO object to be passed to
    a subprocess call that will inhibit a command window from appearing.
    Otherwise, return None.

    Reference: https://stackoverflow.com/a/7006424
    """
    if os.name == 'nt':
        # Module members don't exist on non-Windows machines, suppress type errors.
        info = subprocess.STARTUPINFO()  # type: ignore
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
        return info
    else:
        return None


def tw_quote(text: str) -> str:
    r'''
    Surround the text with appropriate quotes for a macro call
    or HTML attribute in TiddlyWiki.

    >>> tw_quote("No quotes")
    '"No quotes"'

    >>> tw_quote("""Single 'quotes'""")
    '"Single \'quotes\'"'

    >>> tw_quote('Double "quotes"')
    '\'Double "quotes"\''

    >>> tw_quote("""'Single' and "double" quotes""")
    '"""\'Single\' and "double" quotes"""'

    >>> tw_quote('Embedded """triple""" and \'single\' quotes')
    '"""Embedded "_"triple"_" and \'single\' quotes"""'
    '''
    if '"' not in text:
        return '"' + text + '"'
    elif "'" not in text:
        return "'" + text + "'"
    elif '"""' not in text:
        return '"""' + text + '"""'
    else:
        # we have to munge the content or we can't export, TW doesn't have
        # any other options for quoting; replace """ with "_"
        return '"""' + text.replace('"""', '"_"') + '"""'


def uniquify_name(name: str, names: Sequence[str]) -> str:
    """
    Given a tentative name and a list of existing names, return a possibly
    modified new name that is guaranteed not to be the same as any of the existing
    names.

    >>> uniquify_name("Soren", [])
    'Soren'

    >>> uniquify_name("Soren", ["Not Soren"])
    'Soren'

    >>> uniquify_name("Soren", ["Not Soren", "Soren"])
    'Soren 2'

    >>> uniquify_name("Soren", ["Not Soren", "Soren 2", "Soren 3"])
    'Soren'

    >>> uniquify_name("Soren", ["Soren", "Soren 2", "Soren 3"])
    'Soren 4'
    """
    if name not in names:
        return name

    number = 2
    while f"{name} {number}" in names:
        number += 1
    return f"{name} {number}"
