"""
util.py - general-purpose functions and definitions used by multiple modules
"""
import os
import subprocess
from typing import NewType, Optional


Twid = NewType('Twid', str)


def pluralize(sg: str, n: int, pl: str = None) -> str:
    """
    Return a string in one of two forms, depending on whether /n/ is 1.

    For convenience when working with English text, the plural form may be
    left blank if it consists of the singular form plus 's'.
    """
    if n == 1:
        return sg
    else:
        if pl is None:
            pl = sg + 's'
        return pl


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
