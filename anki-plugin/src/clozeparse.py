from collections import Counter
import itertools
from operator import itemgetter
import re
from typing import Iterable, List, Optional, Sequence


class Occlusion:
    def __init__(self, placeholder_index: int, raw_text: str) -> None:
        self.placeholder_index = placeholder_index
        self.raw_text = raw_text
        self.text: Optional[str] = None
        self.anki_index: Optional[int] = None
        self._parse_text()

    @property
    def placeholder(self) -> str:
        return "{%i}" % self.placeholder_index

    @property
    def anki_occlusion(self) -> str:
        assert self.anki_index is not None, \
            "Tried to render occlusion before filling in missing index!"
        return "{{c%i::%s}}" % (self.anki_index, self.text)

    def _parse_text(self) -> None:
        "Fill text and maybe anki_index field from raw_text."
        m = re.match(r'^c(?P<index>[1-9][0-9]*)::(?P<text>.*)', self.raw_text)
        if m:
            self.anki_index = int(m.group('index'))
            self.text = m.group('text')
        else:
            self.text = self.raw_text


def ankify_clozes(text: str) -> str:
    """
    Given some text in TiddlyRemember simplified cloze format, convert it to
    work in Anki. The following documents the simplified format.

    Implicit cloze identification:
        >>> _ankify_clozes("This is a {test}.")
        'This is a {{c1::test}}.'

        >>> _ankify_clozes("{This} is a {test}.")
        '{{c1::This}} is a {{c2::test}}.'

    Explicit cloze identification:
        >>> _ankify_clozes("This is a {c1::test}.")
        'This is a {{c1::test}}.'

        >>> _ankify_clozes("{c1::This} is a {c1::test}.")
        '{{c1::This}} is a {{c1::test}}.'

        >>> _ankify_clozes("{c1::This} is a {c2::test}.")
        '{{c1::This}} is a {{c2::test}}.'

        >>> _ankify_clozes("{c1::This} is a {c2::second} {c3::test}.")
        '{{c1::This}} is a {{c2::second}} {{c3::test}}.'

    A mixture -- the first unused numbers are selected for the implicit matches:
        >>> _ankify_clozes("{c1::This} is a {c2::third} {test}.")
        '{{c1::This}} is a {{c2::third}} {{c3::test}}.'

        >>> _ankify_clozes("{c1::This} is a {c3::fourth} {test}.")
        '{{c1::This}} is a {{c3::fourth}} {{c2::test}}.'

        >>> _ankify_clozes("{c1::This} is a {c3::fourth} {test} {cloze deletion}.")
        '{{c1::This}} is a {{c3::fourth}} {{c2::test}} {{c4::cloze deletion}}.'
    """
    def next_occlusion_number(seq: Sequence[int]) -> Iterable[int]:
        """
        Return natural numbers not yet present in the sequence,
        starting from 1. First any gaps in the sequence are filled,
        then we count upwards to infinity.
        """
        if not seq:
            return itertools.count(1, 1)
        else:
            c = Counter(seq)  # create dict of elements to number of occurrences
            return itertools.chain(
                (i for i in range(1, max(seq)) if c[i] == 0),
                itertools.count(max(seq)+1, 1))

    # Parse out the occlusions and put in clean Python-style placeholders.
    occlusions: List[Occlusion] = []
    def mark_occlusion(match):
        "Save the contents of an occlusion section, then substitute in a placeholder."
        o = Occlusion(len(occlusions), match.group(1))
        occlusions.append(o)
        return o.placeholder
    placeholder_text = re.sub(r'{([^}]*)}', mark_occlusion, text)

    # Fill in cloze numbers for occlusions that used the implicit syntax.
    deferred_mappings = [o for o in occlusions
                         if o.anki_index is None]
    used_occlusion_numbers = [o.anki_index for o in occlusions
                              if o.anki_index is not None]
    for index, occlusion in zip(next_occlusion_number(used_occlusion_numbers),
                                deferred_mappings):
        occlusion.anki_index = index
    
    # Replace placeholders with the cleansed, explicified, Anki-format occlusions.
    return placeholder_text.format(*(i.anki_occlusion for i in occlusions))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
