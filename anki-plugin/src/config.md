# TiddlyRemember Configuration

* **defaultDeck**: The deck that the cards of imported notes will be placed in.
  The ability to use multiple decks is planned for a future version. Currently, TiddlyRemember never moves cards once they have been generated, but this may change in the future.
* **tiddlywikiBinary**: Path to the TiddlyWiki executable on your system.
  Default is `tiddlywiki`, which will work if TW is on your system path.
* **wiki**: Settings for your wiki:
    * **contentFilter**: Only tiddlers matching this filter will be searched for notes. Be sure to exclude tiddlers that cannot be rendered to HTML, such as images or PDFs -- these can cause the sync to crash or take an extremely long time. Be aware that if you make the filter more restrictive and this excludes questions you already have in your collection, *they will be deleted on next sync*, permanently destroying any associated scheduling information if you do not have a valid backup. For safe testing, sync in a new profile and check results.
    * **path**: Path to your wiki -- the folder containing your `tiddlywiki.info` if it's a folder wiki, or the file if it's a file wiki.
    * **permalink**: URL where your wiki can be accessed on the devices you're reviewing on. This will enable you to click a link while reviewing to browse to the tiddler the question comes from. Use a file:/// URL if referring to a file on your computer. This attribute can be removed if you don't want linking.
    * **type**: `folder` or `file`, depending on whether this is a folder wiki or a single-file wiki.
