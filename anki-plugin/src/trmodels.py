"""
trmodels.py - self-constructing definitions of Anki models (note types)

Creating a note type in Anki is a procedural operation, which is very
inconvenient and difficult to read when note types need to be defined in
source code rather than through the GUI. This module allows note types to be
defined declaratively.

It first defines TemplateData and ModelData classes which contain the logic
for creating templates and note types, then subclasses which define the
options and templates for each note type our application needs to create and
manage. A framework for checking if note types exist and have the expected
fields, and for changing between note types defined here, is also provided.

These classes are a bit unusual in that they are never instantiated and have
no instance methods or variables. The class structure is just used as a
convenient way to inherit construction logic and fields and group related
information together.

TiddlyWiki note types defined in twnote.py have a one-to-one relationship
with subclasses of ModelData defined in this module. This relationship is
defined by the TwNote subclasses' /model/ class variable.
"""
from abc import ABC
import inspect
from textwrap import dedent
from typing import Dict, Iterable, List, Optional, Tuple, Type
import sys

import aqt
from anki.consts import MODEL_CLOZE
from anki.models import Template as AnkiTemplate
from anki.models import NoteType as AnkiModel


# Field to hold the unique ID used to maintain synchronization integrity.
# This must (currently) be the same on all note types used by TiddlyRemember
# and is defined here to prevent them from getting out of sync.
ID_FIELD_NAME = 'ID'


class TemplateData(ABC):
    """
    Self-constructing definition for templates.
    """
    name: str
    front: str
    back: str

    @classmethod
    def to_template(cls) -> AnkiTemplate:
        "Create and return an Anki template object for this model definition."
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        mm = aqt.mw.col.models
        t = mm.newTemplate(cls.name)
        t['qfmt'] = dedent(cls.front).strip()
        t['afmt'] = dedent(cls.back).strip()
        return t


class ModelData(ABC):
    """
    Self-constructing definition for models.
    """
    name: str
    fields: Tuple[str, ...]
    templates: Tuple[Type[TemplateData]]
    styling: str
    sort_field: str
    is_cloze: bool

    @classmethod
    def to_model(cls) -> AnkiModel:
        "Create and return an Anki model object for this model definition."
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        mm = aqt.mw.col.models
        model = mm.new(cls.name)
        for i in cls.fields:
            field = mm.newField(i)
            mm.addField(model, field)
        for template in cls.templates:
            t = template.to_template()
            mm.addTemplate(model, t)
        model['css'] = dedent(cls.styling).strip()
        model['sortf'] = cls.fields.index(cls.sort_field)
        if cls.is_cloze:
            model['type'] = MODEL_CLOZE
        return model

    @classmethod
    def in_collection(cls) -> bool:
        """
        Determine if a model by this name exists already in the current
        Anki collection.
        """
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        mm = aqt.mw.col.models
        model = mm.byName(cls.name)
        return model is not None

    @classmethod
    def field_remap(cls, other: 'Type[ModelData]') -> Dict[int, Optional[int]]:
        """
        Produce a field mapping to be used to change a note of this note type
        to that of the /other/ note type. Fields are mapped by index, the old
        note type's index to the new type's index.

        If a field with exactly the same name is found, that is assumed to be
        the correct mapping; otherwise, the check is delegated to the
        other.field_index() class method, which returns None by default
        (simply discard this field). This method can be overridden to support
        maintaining information from certain other note types or fields; for
        TiddlyRemember's purposes right now, we simply let the fields be
        discarded since after changing the note type we will do a
        unidirectional sync that will repopulate them anyway.
        """
        mapping: Dict[int, Optional[int]] = {}
        for idx, field in enumerate(cls.fields):
            try:
                mapping[idx] = other.fields.index(field)
            except ValueError:
                mapping[idx] = other.field_index(cls, field)
        return mapping

    # pylint: disable=unused-argument
    @classmethod
    def field_index(cls, from_type: 'Type[ModelData]',
                    from_field_name: str) -> Optional[int]:
        """
        Return the index of the field in *this* note type that the field
        from_field_name in the note type from_type maps onto, or None if the content
        should be discarded.
        """
        return None

    @classmethod
    def verify_integrity(cls, anki_model: AnkiModel) -> None:
        """
        Raise an exception if the user has changed the model in a way that will
        interfere with syncing.

        This currently means changing the order or names of fields or
        the type (cloze or regular). Changing the templates is fine and supported.
        """
        # Verify field names and order.
        anki_fields = ((f['ord'], f['name']) for f in anki_model['flds'])
        for (anki_ord, anki_name), (mod_ord, mod_name) in zip(anki_fields,
                                                              enumerate(cls.fields)):
            if not anki_ord == mod_ord and anki_name == mod_name:
                raise Exception(
                    f"The fields on the note type {cls.name} have been modified "
                    f"in a way that prevents TiddlyRemember from syncing. Please "
                    f"restore the fields to their standard names and positions, "
                    f"then try syncing again.")

        # Verify model type.
        if cls.is_cloze and not anki_model['type'] == MODEL_CLOZE:
            raise Exception(
                f"TiddlyRemember expects the note type {cls.name} to be a cloze note "
                f"type, but it is not! Please fix the note type, then try syncing "
                f"again.")
        elif not cls.is_cloze and anki_model['type'] == MODEL_CLOZE:
            raise Exception(
                f"TiddlyRemember expects the note type {cls.name} to be a standard "
                f"note type, but it is a cloze note type! Please fix the note type, "
                f"then try syncing again.")



class TiddlyRememberQuestionAnswer(ModelData):
    "One-sided Q&A note."
    class TiddlyRememberQuestionAnswerTemplate(TemplateData):
        "Template for the Q&A note."
        name = "Forward"
        front = """
            {{Question}}
        """
        back = """
            {{FrontSide}}

            <hr id=answer>

            {{Answer}}

            <div class="note-id">
                {{#Permalink}}
                    [<a href="{{text:Permalink}}">{{Wiki}}/{{Reference}}</a> {{ID}}]
                {{/Permalink}}
                {{^Permalink}}
                    [{{Wiki}}/{{Reference}} {{ID}}]
                {{/Permalink}}
            </div>
        """

    name = "TiddlyRemember Q&A v1"
    fields = ("Question", "Answer", ID_FIELD_NAME, "Wiki", "Reference", "Permalink")
    templates = (TiddlyRememberQuestionAnswerTemplate,)
    styling = """
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }

        .note-id {
            font-size: 70%;
            margin-top: 1ex;
            text-align: right;
            color: grey;
        }

        .note-id a {
            color: grey;
        }
    """
    sort_field = "Question"
    is_cloze = False


class TiddlyRememberCloze(ModelData):
    "Cloze deletion note."
    class TiddlyRememberClozeTemplate(TemplateData):
        "Template for the cloze note."
        name = "Cloze"
        front = """
            {{cloze:Text}}
        """
        back = """
            {{cloze:Text}}

            <div class="note-id">
                {{#Permalink}}
                    [<a href="{{text:Permalink}}">{{Wiki}}/{{Reference}}</a> {{ID}}]
                {{/Permalink}}
                {{^Permalink}}
                    [{{Wiki}}/{{Reference}} {{ID}}]
                {{/Permalink}}
            </div>
        """

    name = "TiddlyRemember Cloze v1"
    fields = ("Text", ID_FIELD_NAME, "Wiki", "Reference", "Permalink")
    templates = (TiddlyRememberClozeTemplate,)
    styling = """
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }

        .cloze {
            font-weight: bold;
            color: blue;
        }

        .nightMode .cloze {
            filter: invert(85%);
        }

        .note-id {
            font-size: 70%;
            margin-top: 1ex;
            text-align: right;
            color: grey;
        }

        .note-id a {
            color: grey;
        }
    """
    sort_field = "Text"
    is_cloze = True


def _itermodels() -> Iterable[Type[ModelData]]:
    "Iterable over the set of all model definitions in this file."
    def is_model(obj):
        return (inspect.isclass(obj)
                and any(b.__name__ == 'ModelData' for b in obj.__bases__))
    return (i for _, i in inspect.getmembers(sys.modules[__name__], is_model))


def all_note_types() -> List[Type[ModelData]]:
    """
    Return a list of all note types defined in this file.
    """
    return list(_itermodels())


def by_name(model_name: str) -> Optional[Type[ModelData]]:
    """
    Return a note type defined in this file by its name, or None if no such note
    type exists.
    """
    try:
        return next(i for i in all_note_types() if i.name == model_name)
    except StopIteration:
        return None


def ensure_note_types() -> None:
    """
    For all note types defined in this file, add them to the collection if
    they aren't in there already.
    """
    assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
    for model in _itermodels():
        if not model.in_collection():
            aqt.mw.col.models.add(model.to_model())


def verify_note_types() -> None:
    """
    Raise an exception if any of the TiddlyRemember note types have been altered
    in a way that could prevent a safe and correct sync.

    The caller should ensure that all of the TiddlyRemember note types exist in Anki
    (this is checked by name) before calling verify_note_types().
    """
    for model in _itermodels():
        assert aqt.mw is not None, "Verified note types before Anki was loaded!"
        anki_model = aqt.mw.col.models.byName(model.name)
        model.verify_integrity(anki_model)
