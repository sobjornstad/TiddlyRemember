# TiddlyRemember

TiddlyRemember is a tool that integrates [TiddlyWiki][] with [Anki][].
You can interleave questions with your notes in TiddlyWiki,
    then sync them into Anki notes with one click.
You can edit and move the questions around your TiddlyWiki,
    and they will stay connected to the Anki notes.
Scheduling information in Anki is preserved when editing notes in TiddlyWiki.

## Documentation

Installation and use instructions can be found at
https://TODO.com.


## Building from source

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
