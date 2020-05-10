from anki.notes import Note

class TwNote:
    def __init__(self, id_: str, tidref: str, question: str, answer: str) -> None:
        self.id_ = id_
        self.tidref = tidref
        self.question = question
        self.answer = answer

    def __repr__(self):
        return (f"Note(id_={self.id_!r}, tidref={self.tidref!r}, "
                f"question={self.question!r}, answer={self.answer!r}")

    def __eq__(self, other):
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_)

    def fields_equal(self, anki_note: Note) -> bool:
        """
        Compare the fields on this TwNote to an Anki note. Return True if all
        are equal.
        """
        return (
            self.question == anki_note.fields[0]
            and self.answer == anki_note.fields[1]
            and self.id_ == anki_note.fields[2]
            and self.tidref == anki_note.fields[3]
        )

    def update_fields(self, anki_note: Note) -> None:
        """
        Alter the Anki note to match this TiddlyWiki note.
        """
        anki_note.fields[0] = self.question
        anki_note.fields[1] = self.answer
        anki_note.fields[3] = self.tidref
