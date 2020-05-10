# TiddlyRemember

TiddlyRemember is a tool that integrates [TiddlyWiki][] with [Anki][].
You can interleave questions with your notes in TiddlyWiki,
    then sync them into Anki notes with one click.
You can edit and move the questions around your TiddlyWiki,
    and they will stay connected to the Anki notes.
Scheduling information in Anki is preserved when editing notes in TiddlyWiki.

Why would you want to create Anki notes from TiddlyWiki?

* One of the problems with using spaced repetition to study complex topics
  is that individual cards end up largely without context,
  at least if you're following the Minimum Information Principle,
  and if you need a refresher, it's hard to find the original source.
  TiddlyRemember can take you right back to your notes.
* If you already have notes on a topic,
  this can help keep your content more [DRY][] --
  you don't have to maintain the same knowledge in two places.
* You can easily add notes to your Anki collection
  at the same time you're taking narrative or outline notes,
  without having to switch back and forth between two applications.
  As a student, I have often been faced with
  choosing between taking notes or creating Anki cards during a lecture,
  knowing I would not have the time or motivation to go through
  and also create Anki cards afterwards.

**TiddlyRemember is still quite alpha.**
Formats and working methods are subject to change without notice.
I have worked on it for half a weekend and barely even used it myself yet!

[TiddlyWiki]: https://tiddlywiki.com/
[Anki]: https://apps.ankiweb.net
[DRY]: https://github.com/buildinspace/peru


## Installation

Install the TiddlyWiki plugin in the `tw-plugin/` subdirectory
    directly to your Node.JS wiki
    (I like using [Peru][] to manage plugins)
    or build it into a TiddlyWiki plugin using the [dev instructions][]
    and then install it in your single-file wiki.
TiddlyWiki >=5.1.22 is required
    (less may work, but you'll have to modify the plugin metadata -- I haven't tested it).
You will also need TiddlyWiki running on Node on your machine.
You don't have to actually host your wiki on Node --
    single files work fine --
    -- but you do have to have it available to do the rendering
    the plugin requires to extract questions.

Run `make` in the `anki-plugin` directory.
PyQt5 needs to be installed to do this
    (try `pip install -r requirements.txt` to get all the devtools).
Then copy the `anki-plugin/src` directory
    to your Anki plugins folder (>=2.1.20 is assumed).
Configure the Anki plugin with Tools -> Add-ons -> Configure,
    following the instructions to the right of the JSON.

[Peru]: https://github.com/buildinspace/peru
[dev instructions]: https://tiddlywiki.com/dev/#Developing%20plugins%20using%20Node.js%20and%20GitHub


## Use

Currently, question-and-answer pairs are supported
    with the use of the `rememberq` TiddlyWiki macro.
Support for cloze deletions is planned.
Here's an example:

```
<<rememberq "a_unique_id"
    "What is the answer to life, the universe, and everything?"
    "42."
>>
```

This will render the question-and-answer pair in a pretty way
    and insert enough information in the HTML
    that the TiddlyRemember parser can pick it out.
The parser actually renders the tiddlers,
    so you can include TextReferences and so on within the macro parameters
    and the referents will display both in the browser and on your Anki cards.
However, HTML will be stripped when creating Anki notes,
    so links, text formatting, etc., will only show up in your wiki;
    this may change in the future.

Clicking the lightbulb icon on the edit toolbar
    will insert this snippet,
    including the current time down to the milliseconds as the unique ID,
    so you don't have to worry about creating one.

After you've added, edited, or removed questions in TiddlyWiki,
    choose **Tools -> Sync from TiddlyWiki** in Anki
    to update your collection to match.


## Cross-referencing

If you define the `permalink` property in your Anki plugin config,
    a link will appear on your cards
    which you can click to get back to the tiddler that contains the question.
Even if you don't, the name of the tiddler will be shown.
Going the other way,
    the unique ID of each question appears next to the question in TiddlyWiki;
    to find the associated Anki card,
    search for `ID:theuniqueid` in the browser.


## Limitations and gotchas

* Sync is unidirectional.
  Any changes you make in Anki will be overwritten without warning on your next sync.
  There are no plans to change this, and doing so would break other things
  (e.g., the ability to include transclusions inside a question or answer).
* All questions go to a single deck and have no tags.
  Currently, you can move cards to a different deck or add tags
  and they will be preserved across syncs.
  However, this will likely change in future versions
  so that this is instead configured within your wiki or question macros
  and overwrites any changes made in Anki,
  so you probably should not do complicated organization now.
* If you delete questions in TiddlyWiki,
  they will be permanently removed from Anki,
  and the scheduling information cannot be recovered except by restoring a backup.
  Most of the time, this is probably what you want,
  but be aware it will happen!
  Moving a question within a tiddler or between tiddlers is fine though,
  as long as you save the question in the new location
  prior to running a sync in Anki.
* Only one wiki is supported per Anki installation at the moment.
  Multiple-wiki support is planned in the future.
  If you switch to a new wiki in the same profile,
  *all your existing notes will be deleted*
  (you can avoid this by first switching them to a different note type).
* If the same unique ID is used for multiple `rememberq` calls,
  one definition of the question will randomly overwrite the other in Anki.
  Don't do this!
* If you transclude a tiddler containing questions into another tiddler,
  which tiddler is referenced as the source will be random;
  TiddlyRemember is not able to follow transclusions to find the original source,
  as it starts looking for questions
  only after TiddlyWiki has completely rendered all tiddlers.
* Your TiddlyWiki needs to be on your desktop filesystem for now.
  If you keep it in cloud storage such as TiddlySpot,
  you'll need to download the wiki
  and save it to the location specified in your Anki plugin configuration
  before each sync.
