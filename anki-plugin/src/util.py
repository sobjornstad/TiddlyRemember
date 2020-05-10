from typing import NewType

Twid = NewType('Twid', str)

def pluralize(sg: str, n: int, pl: str = None) -> str:
    if n == 1:
        return sg
    else:
        if pl is None:
            pl = sg + 's'
        return pl
