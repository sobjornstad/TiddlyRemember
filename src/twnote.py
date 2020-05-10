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

