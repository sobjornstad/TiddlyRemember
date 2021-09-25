"""
clozeparse.py - transform TiddlyRemember cloze deletions into a format Anki understands

This module's public interface consists of the ankify_clozes() function.
To change the argument of the remembercz TiddlyWiki macro into suitable
text for the Text field of an Anki cloze note, simply call this function
on that argument.
"""
from collections import Counter
import itertools
import re
from typing import Iterable, List, Optional, Sequence

from .oops import UnmatchedBracesError


class Occlusion:
    """
    Representation of an occlusion -- a part within a remembercz TiddlyWiki note
    that is in {single braces} and needs to become an Anki occlusion.

    Constructed from a placeholder index (this will be used to substitute the
    occlusion back into the text of the note once parsing is done) and raw_text
    (the part that was between the {braces} in the original user-entered text).
    """
    def __init__(self, placeholder_index: int, raw_text: str) -> None:
        self.placeholder_index = placeholder_index
        self.raw_text = raw_text
        self.text: Optional[str] = None
        self.anki_index: Optional[int] = None
        self._parse_text()

    @property
    def placeholder(self) -> str:
        "A Python format-string placeholder for this occlusion."
        return "©<%i>©" % self.placeholder_index

    @property
    def anki_occlusion(self) -> str:
        """
        This occlusion, in the form that Anki understands.

        The caller must ensure that it has filled in self.anki_index if this
        Occlusion was originally constructed from an implicitly numbered
        occlusion (one that looks like {this}, rather than an {{c1::explicit
        occlusion}}).
        """
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


def ankify_clozes(text: str, wiki_name: str = "", tidref: str = "") -> str:
    r"""
    Given some text in TiddlyRemember simplified cloze format, convert it to
    work in Anki. The following documents the simplified format.

    Implicit cloze identification:
        >>> ankify_clozes("This is a {test}.")
        'This is a {{c1::test}}.'

        >>> ankify_clozes("{This} is a {test}.")
        '{{c1::This}} is a {{c2::test}}.'

    Explicit cloze identification:
        >>> ankify_clozes("This is a {c1::test}.")
        'This is a {{c1::test}}.'

        >>> ankify_clozes("{c1::This} is a {c1::test}.")
        '{{c1::This}} is a {{c1::test}}.'

        >>> ankify_clozes("{c1::This} is a {c2::test}.")
        '{{c1::This}} is a {{c2::test}}.'

        >>> ankify_clozes("{c1::This} is a {c2::second} {c3::test}.")
        '{{c1::This}} is a {{c2::second}} {{c3::test}}.'

    A mixture -- the first unused numbers are selected for the implicit matches:
        >>> ankify_clozes("{c1::This} is a {c2::third} {test}.")
        '{{c1::This}} is a {{c2::third}} {{c3::test}}.'

        >>> ankify_clozes("{c1::This} is a {c3::fourth} {test}.")
        '{{c1::This}} is a {{c3::fourth}} {{c2::test}}.'

        >>> ankify_clozes("{c1::This} is a {c3::fourth} {test} {cloze deletion}.")
        '{{c1::This}} is a {{c3::fourth}} {{c2::test}} {{c4::cloze deletion}}.'

    Braces escaped with a backslash:
        >>> ankify_clozes(r"Here is a {sentence} with some \{escaped braces\}.")
        'Here is a {{c1::sentence}} with some {escaped braces}.'

        >>> ankify_clozes(r"How about {double escapes} like \\{this\\}?")
        'How about {{c1::double escapes}} like \\{this\\}?'

        >>> ankify_clozes(r"For LaTeX grouping, use {`\{braces\}`}.")
        'For LaTeX grouping, use {{c1::`{braces}`}}.'

    Syntax mistakes:
        >>> ankify_clozes("Unclosed {braces just don't produce a cloze.")
        "Unclosed {braces just don't produce a cloze."

        >>> ankify_clozes("Unopened braces just don't produce} a cloze.")
        "Unopened braces just don't produce} a cloze."

        >>> ankify_clozes("Backwards braces }don't produce{ a cloze either.")
        "Backwards braces }don't produce{ a cloze either."

        >>> ankify_clozes("This is the {c3::first} cloze.")
        'This is the {{c3::first}} cloze.'

        (That one's weird but totally acceptable to Anki.)
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
    placeholder_text = re.sub(r'(?<!\\){(.*?)(?<!\\)}', mark_occlusion, text)

    # Fill in cloze numbers for occlusions that used the implicit syntax.
    deferred_mappings = [o for o in occlusions
                         if o.anki_index is None]
    used_occlusion_numbers = [o.anki_index for o in occlusions
                              if o.anki_index is not None]
    for index, occlusion in zip(next_occlusion_number(used_occlusion_numbers),
                                deferred_mappings):
        occlusion.anki_index = index

    # Replace placeholders with the cleansed, explicified, Anki-format occlusions.
    occ_lookup = {o.placeholder_index: o for o in occlusions}
    def replace_placeholder(match):
        return occ_lookup[int(match.group(1))].anki_occlusion
    cloze_text = re.sub(r'©<([0-9]+)>©', replace_placeholder, placeholder_text)
    return re.sub(r'\\([{}])', r'\1', cloze_text)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
