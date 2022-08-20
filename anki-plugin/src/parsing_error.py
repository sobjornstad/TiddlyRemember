"""
Dialog showing which tiddler experienced a parsing error.
"""

import traceback

# pylint: disable=import-error, no-name-in-module
import aqt
from aqt.qt import QDialog

from aqt.qt import qtmajor
if qtmajor > 5:
    from . import parsing_error_dialog6 as parsing_error_dialog
else:
    from . import parsing_error_dialog5 as parsing_error_dialog  # type: ignore

# pylint: disable=wrong-import-position
from .oops import TiddlerParsingError


class ParsingErrorDialog(QDialog):
    """
    Friendly interface to the add-on's JSON config. Lets you specify general options
    and details of which wikis to sync.
    """

    def __init__(self, exc: TiddlerParsingError) -> None:
        super().__init__()
        assert aqt.mw is not None, "Settings dialog launched before Anki initialized!"
        self.mw: aqt.AnkiQt = aqt.mw
        self.form = parsing_error_dialog.Ui_Dialog()
        self.form.setupUi(self)

        self.form.moreButton.clicked.connect(self.onMoreButton)
        self.form.okButton.clicked.connect(self.accept)

        self.form.tiddlerNameLabel.setText(exc.tiddler_name)
        self.form.errorText.setPlainText(
            "".join(traceback.TracebackException.from_exception(exc).format())
        )
        self.onMoreButton()

    def onMoreButton(self) -> None:
        "Toggle showing the full error text."
        if self.form.moreButton.text() == "More >>":
            # Show the full error text.
            self.resize(self.sizeHint().width(), 400)
            self.form.moreButton.setText("<< Less")
            self.form.errorText.setMaximumHeight(300)
            self.form.errorText.show()
        else:
            # Hide the error text.
            # NOTE: For some reason the second time this is called, the window doesn't
            # resize to the correct size (there's extra space at the top and bottom).
            # This is not presently worth fixing.
            self.form.moreButton.setText("More >>")
            self.form.errorText.hide()
            self.form.errorText.setMaximumHeight(0)
            self.resize(self.sizeHint().width(), 80)
