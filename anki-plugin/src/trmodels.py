from abc import ABC
import inspect
from textwrap import dedent
from typing import Iterable, List, Type, Tuple
import sys

import aqt
from anki.consts import MODEL_CLOZE


class TemplateData(ABC):
    """
    Self-constructing definition for templates.
    """
    name: str
    front: str
    back: str

    @classmethod
    def to_template(cls):
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
    def to_model(cls):
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
    def in_collection(cls):
        mm = aqt.mw.col.models
        model = mm.byName(cls.name)
        return model is not None



class TiddlyRememberQuestionAnswer(ModelData):
    class TiddlyRememberQuestionAnswerTemplate(TemplateData):
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
                    [<a href="{{text:Permalink}}">{{Reference}}</a>:{{ID}}]
                {{/Permalink}}
                {{^Permalink}}
                    [{{Reference}}:{{ID}}]
                {{/Permalink}}
            </div>
        """

    name = "TiddlyRemember Q&A v1"
    fields = ("Question", "Answer", "ID", "Reference", "Permalink")
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
    class TiddlyRememberClozeTemplate(TemplateData):
        name = "Cloze"
        front = """
            {{cloze:Text}}
        """
        back = """
            {{cloze:Text}}

            <div class="note-id">
                {{#Permalink}}
                    [<a href="{{text:Permalink}}">{{Reference}}</a>:{{ID}}]
                {{/Permalink}}
                {{^Permalink}}
                    [{{Reference}}:{{ID}}]
                {{/Permalink}}
            </div>
        """

    name = "TiddlyRemember Cloze v1"
    fields = ("Text", "ID", "Reference", "Permalink")
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
    def is_model(obj):
        return (inspect.isclass(obj)
                and any('ModelData' == b.__name__ for b in obj.__bases__))
    return (i for _, i in inspect.getmembers(sys.modules[__name__], is_model))


def ensure_note_types():
    """
    For all note types defined in this file, add them to the collection if
    they aren't in there already.
    """
    for model in _itermodels():
        if not model.in_collection():
            aqt.mw.col.models.add(model.to_model())


def all_note_types() -> List[Type[ModelData]]:
    """
    Return a list of all note types defined in this file.
    """
    return list(_itermodels())