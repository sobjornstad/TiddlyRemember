# TiddlyRemember Configuration

* **defaultDeck**: The deck that the cards of imported notes will be placed in, if there is no match in your deck mappings (see the manual for details on deck mappings).
* **tiddlywikiBinary**: Path to the TiddlyWiki executable on your system.
  Default is `tiddlywiki`, which will work if TW is on your system path.
* **wiki**: Settings for your wiki:
    * **contentFilter**: Only tiddlers matching this filter will be searched for notes. Be sure to exclude tiddlers that cannot be rendered to HTML, such as images or PDFs -- these can cause the sync to crash or take an extremely long time. Be aware that if you make the filter more restrictive and this excludes questions you already have in your collection, *they will be deleted on next sync*, permanently destroying any associated scheduling information if you do not have a valid backup. For safe testing, sync in a new profile and check results.
    * **path**: Path to your wiki -- the folder containing your `tiddlywiki.info` if it's a folder wiki, the file if it's a file wiki on your local filesystem, or the URL if it's a file wiki at a URL.
    * **permalink**: URL where your wiki can be accessed on the devices you're reviewing on. This will enable you to click a link while reviewing to browse to the tiddler the question comes from. Use a file:/// URL if referring to a file on your computer. This attribute can be removed if you don't want linking.
    * **type**: `folder`, `file`, or `url`, depending on whether this is a folder wiki, a single-file wiki on your local computer, or the URL of a single-file wiki available on the web. file:/// URLs do not work here (use a type of `file` for that).
