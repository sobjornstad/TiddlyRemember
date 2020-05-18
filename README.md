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

TiddlyRemember can generate question-and-answer pairs and cloze deletions.
We'll start by looking at pairs; cloze deletions work similarly.

### Q&A 

Question-and-answer cards are created with the `rememberq` TiddlyWiki macro.
Here's an example:

```
<<rememberq "a_unique_id"
    "What is the answer to life, the universe, and everything?"
    "42."
>>
```

This will render the question-and-answer pair in a new paragraph
    and insert information in the HTML
    that the TiddlyRemember parser can pick out.
The parser actually renders the tiddlers when you sync to Anki,
    so you can include TextReferences and so on within the macro parameters
    and the referents will display both in your wiki and on your Anki cards.
However, HTML will be stripped when creating Anki notes,
    so links, text formatting, etc., will only show up in your wiki;
    this may change in the future.

Clicking the white (left-hand) lightbulb icon on the edit toolbar
    will insert this snippet,
    including the current time down to the milliseconds as the unique ID,
    so you don't have to worry about creating one.

After you've added, edited, or removed questions in TiddlyWiki,
    choose **Tools -> Sync from TiddlyWiki** in Anki
    to update your collection to match.

### Cloze deletions

Cloze deletions work much like questions,
    but they use the `remembercz` macro,
    which can be inserted with the black (right-hand) lightbulb icon on the edit toolbar.
The portions you want to occlude (delete/hide) go in *single* braces:
    Anki uses double braces, but TiddlyWiki already uses this for transclusions,
    which are valid within the macro as well.
The simplest way is to use *implicit cloze numbering*:
    place each part you want to occlude in braces,
    and Anki will create one card for each occlusion:

```
<<remembercz "a_unique_id"
    "The answer to {life, the universe, and everything} is {42}."
>>
```

This will generate two Anki cards.
The front will show as follows,
    while the back will show the entire sentence:

1. The answer to [...] is 42.
2. The answer to life, the universe, and everything is [...].

If you want to put more than one occlusion on a card,
    you can use *explicit cloze numbering*, like so:

```
<<remembercz "a_unique_id"
    "The answer to {c1::life}, the {c1::universe}, and {c1::everything} is {c2::42}."
>>
```

With the result:

1. The answer to [...], the [...], and [...] is 42.
2. The answer to life, the universe, and everything is [...].

Cloze deletions can also be rendered *inline*,
    as part of a paragraph in your wikitext,
    rather than as a separate paragraph.
This has no effect on the note generated in Anki.
To do this, simply add the `inline` third argument to the `remembercz` macro:

```
The world is full of silly trivia.
For instance, <<remembercz "a_unique_id"
    "the answer to {c1::life}, the {c1::universe}, and {c1::everything} is {c2::42}."
    inline>>
The question, of course, is uncertain.
```


## Choosing decks and tags

By default, cards go to the deck specified in the `defaultDeck` property
    of your Anki add-on configuration
    (this property, itself, defaults to `TiddlyRemember`),
and notes have no tags.

You can configure how questions map to decks and tags
    on a tiddler-by-tiddler basis
    by overriding the configuration tiddlers
    `$:/config/TiddlyRemember/TagMapping`
    and `$:/config/TiddlyRemember/DeckMapping`.
These tiddlers are empty in a base installation.
You may populate them with a newline-separated list of TiddlyWiki filters.
TiddlyRemember will run each filter
    against the title of the tiddler your question is in
    and track results across the filter runs.
(If you're familiar with the way Node folder wikis
 use `$:/config/FileSystemPaths` to define folder structure,
 this is the same idea.)

### Tag details

For tags, all matches in any of the filters become tags,
    duplicates excluded.
If your tags contain spaces, the spaces will be turned into `_`
    (Anki separates tags by spaces).
If there are no results at all, the card gets no tags.

Here's an example tag mapping,
    which passes through all tags set in TiddlyWiki
    with the exception of the `Public` tag,
    and additionally includes an `Important` tag
    for questions in tiddlers with a `priority` field set to "high":

```
[tags[]] -[[Public]]
[has[priority]get[priority]match[high]then[Important]]
```


### Deck details

Decks work similarly to tags.
However, since a card can only be in one deck,
    the first result returned by any of the filters wins
    and the remaining results are ignored.
If there are no results at all,
    the `defaultDeck` in your Anki settings is used.
Decks will be created on sync if they don't exist,
    but won't be deleted even if the sync makes them empty.


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
* If the same unique ID is used for multiple `rememberq` or `remembercz` calls,
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
* Implicit cloze numbering can occasionally cause confusing/incorrect scheduling.
  See the **Caution on implicit cloze numbering**, below.


### Caution on implicit cloze numbering

Implicit cloze numbering is very convenient,
    but editing implicitly-numbered cloze deletions
    can occasionally cause Anki to schedule the changed cards incorrectly.
Most people rarely add or remove occlusions from an existing cloze deletion,
    but it's worth being aware that this can happen if you do.
Specifically, this happens if you *insert or remove an occlusion*
    other than the rightmost one.
This is because TiddlyRemember numbers implicit clozes from left to right,
    and Anki tracks scheduling based on the number of the occlusion.

For instance, if you have:

```
My two favorite letters are {L} and {R}.
```

And then you change it to:

```
My three favorite letters are {L}, {M}, and {R}.
```

Previously, the card where R was occluded was numbered **2**.
Now, R will be numbered **3** --
    and M will be numbered **2**,
    so it will retain the scheduling of R,
    while R will be treated as a new card!

Fortunately, this is easy to prevent -- just switch to explicit numbering
    if you need to insert or remove occlusions in an existing cloze deletion,
    keeping the numbers of the existing occlusions:

```
My three favorite letters are {c1::L}, {c3::M}, and {c2::R}.
```

If this sounds too complicated,
    you can simply use explicit numbering in all cases --
    or if that seems like too much of a burden,
    just not worry about the scheduling being wrong on rare occasions.
