"""
importer.py - orchestrate the import/synchronization process from the GUI side

The import process has three broad stages:

1. **Initialization**: Set up the dialog and confirm the configuration is correct.
2. **Extraction**: The wiki is downloaded and/or turned into a folder wiki in the
   system's temporary directory if needed, then each tiddler listed in the configured
   filter is rendered through the TiddlyRemember template to HTML and parsed by
   TiddlyRemember note type classes. These classes output zero or more TiddlyRemember
   notes for each tiddler, and these notes are gathered together into a set.
3. **Syncing**: The TiddlyRemember notes are compared to the notes in the user's Anki
   collection, and notes in the user's Anki collection are added, updated, or deleted
   to match the set of TiddlyRemember notes.

Extraction is carried out by the `:meth:extract()` method of :class:`ImportDialog()`,
which relies primarily on `:meth:twimport.find_notes()`,
while syncing is carried out in the `:meth:join_thread()` method
of :class:`ImportDialog()`, which relies primarily on :meth:`ankisync.sync()`.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from aqt.utils import askUser, showText, showWarning, tooltip
# pylint: disable=import-error, no-name-in-module
from aqt.qt import QDialog, QThread, pyqtSignal

from aqt.qt import qtmajor
if qtmajor > 5:
    from . import import_dialog6 as import_dialog
else:
    from . import import_dialog5 as import_dialog  # type: ignore

# pylint: disable=wrong-import-position
from . import ankisync
from .oops import ConfigurationError, RenderingError
from . import twimport
from .twnote import TwNote
from .util import pluralize


class ImportThread(QThread):
    """
    Background thread to export a wiki and parse questions out of it.
    """
    progress_update = pyqtSignal(int, int)

    def __init__(self, conf: dict, wiki_name: str, wiki_conf: Dict[str, str]) -> None:
        super().__init__()
        self.conf = conf
        self.wiki_name = wiki_name
        self.wiki_conf = wiki_conf
        self.notes: Optional[Set[TwNote]] = None
        self.exception: Optional[Exception] = None
        self.warnings: List[str] = []

    def run(self) -> None:
        "Find notes, updating owner on progress periodically."
        try:
            self.notes = twimport.find_notes(
                tw_binary=self.conf['tiddlywikiBinary'],
                wiki_path=self.wiki_conf['path'],
                wiki_type=self.wiki_conf['type'],
                wiki_name=self.wiki_name,
                filter_=self.wiki_conf['contentFilter'],
                password=self.wiki_conf.get('password', ''),
                callback=self.progress_update.emit,
                warnings=self.warnings,
            )
            for n in self.notes:
                wiki_url = self.wiki_conf.get('permalink', '')
                if wiki_url:
                    n.set_permalink(wiki_url)
        except Exception as e:
            self.exception = e


class ImportDialog(QDialog):
    """
    Dialog implementing asynchronous extraction from TiddlyWiki,
    followed by synchronization with an Anki collection.
    """
    def __init__(self, mw) -> None:
        QDialog.__init__(self)
        self.form = import_dialog.Ui_Dialog()
        self.form.setupUi(self)
        self.conf = mw.addonManager.getConfig(__name__)
        self.mw = mw

        self.extract_thread: Optional[ImportThread] = None
        self.notes: Set[TwNote] = set()
        self.warnings: List[str] = []
        self.wikis = list(self.conf['wikis'].items())
        self.form.wikiProgressBar.setMaximum(len(self.wikis))

    def start_import(self) -> bool:
        """
        Check to make sure import is configured correctly and begin
        extracting data. Return True if started asynchronously, False if
        unable to start.
        """
        # Catch scenario where user tries to sync without configuring and provide
        # a helpful error message.
        if len(self.wikis) == 1 and not self.wikis[0][1]['path'].strip():
            showWarning("You don't appear to have set up any wikis to sync with. "
                        "To do so, choose Tools > Add-ons, select TiddlyRemember, "
                        "and click the Config button.")
            return False

        self.extract()
        return True

    def extract_progress(self, at: int, end: int) -> None:
        "Progress callback function for export/parse triggered by progress signal."
        self.form.progressBar.setMaximum(100)
        self.form.text.setText(f"Extracting notes from tiddlers...{at}/{end}")
        if end == 0:
            # Obviously this will be done *real* soon...but don't want an exception!
            self.form.progressBar.setValue(100)
        else:
            self.form.progressBar.setValue(at * 100 / end)

    def extract(self) -> None:
        """
        Extract questions from a TiddlyWiki using Node. When done, proceed to
        sync with Anki.
        """
        wiki_name, wiki_conf = self.wikis.pop()

        self.form.text.setText(f"Exporting tiddlers from {wiki_name}...")
        self.form.progressBar.setMaximum(0)

        self.extract_thread = ImportThread(self.conf, wiki_name, wiki_conf)
        self.extract_thread.finished.connect(self.join_thread)  # type: ignore
        self.extract_thread.progress_update.connect(self.extract_progress)
        self.extract_thread.start()

    def handle_thread_exception(self) -> bool:
        """
        Try to handle exceptions that took place during the thread's execution,
        if any.

        Three possible results:
            - There were no exceptions: False is returned.
            - There was an exception and a warning was displayed, so no further
              processing should be done: True is returned.
            - There was an exception we didn't know how to handle:
              the exception is reraised.
        """
        assert self.extract_thread is not None, \
            "Tried to handle exceptions on a nonexistent thread!"

        exc = self.extract_thread.exception
        if exc:
            self.reject()

            if isinstance(exc, ConfigurationError):
                showWarning(str(self.extract_thread.exception))
            elif isinstance(exc, RenderingError) and 'ENAMETOOLONG' in str(exc):
                msg = ("It looks like your wiki may contain a tiddler with an "
                       "extremely long name, which cannot be synced due to "
                       "limits on the length of a filename in your operating system. "
                       "Please reduce the length of this tiddler name "
                       "and then try syncing again. "
                       "The exact length allowed will depend on your operating system "
                       "and the language your tiddler title is written in, "
                       "but should generally not be more than 200 characters "
                       "(sometimes less).")
                m = re.search(r"^\s*path: '(?P<path>.*)'\s*$", str(exc),
                              flags=re.MULTILINE)
                if m:
                    msg += f"\n\nTiddler path: {m['path']}"
                msg += f"\n\nThe original error message follows:\n{str(exc)}"
                showWarning(msg)
            else:
                raise exc

            return True
        return False

    def join_thread(self) -> None:
        """
        Gather up the results of a completed extract thread, and start the next one
        if appropriate.
        """
        assert self.extract_thread is not None, "Tried to join a nonexistent thread!"

        if self.handle_thread_exception():
            return None

        if not self.extract_thread.notes:
            # This is probably a mistake or misconfiguration. To avoid deleting
            # all the user's existing notes to "sync" the collection, abort now.
            showWarning(
                f"No notes were found in the wiki {self.extract_thread.wiki_name}. "
                f"Please check your add-on configuration. "
                f"Your collection has not been updated.")
            self.reject()
            return None

        # This is a set union, with object equality defined by the ID. Any
        # notes with an ID matching one already used in a previous wiki will be
        # discarded here.
        self.notes.update(self.extract_thread.notes)
        self.warnings.extend(self.extract_thread.warnings)

        self.form.wikiProgressBar.setValue(self.form.wikiProgressBar.value() + 1)
        if self.wikis:
            # If there are any more wikis, handle the next one.
            # Eventually, parallelizing this might be nice
            # (might also not improve performance).
            return self.extract()
        else:
            # When all are completed...
            if self.warnings:
                showText(
                    f"*** {len(self.warnings)} "
                    f"{pluralize('warning', len(self.warnings))}: ***\n"
                    + '\n'.join(self.warnings)
                )
            if (not self.warnings) or askUser("Continue syncing?"):
                return self.sync()
            else:
                self.accept()
                self.mw.reset()
                return tooltip("Sync canceled.")

    def sync(self) -> None:
        """
        Compare the notes gathered by the various wiki threads with the notes
        currently in our Anki collection and add, edit, and remove notes as needed
        to get Anki in sync with the TiddlyWiki notes.
        """
        self.form.progressBar.setMaximum(0)
        self.form.text.setText("Applying note changes to your collection...")
        userlog = ankisync.sync(self.notes, self.mw.col, self.conf['defaultDeck'])

        self.accept()
        self.mw.reset()
        tooltip(userlog)
