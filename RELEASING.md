Since Anki doesn't have any way to deploy plugins through CD,
    I'm inclined to put off developing a real pipeline
    for the parts I can automate,
    so in the meantime,
    here's at least a consistent set of manual release steps.


## Changing the docs

Aside from straight bugfix releases,
    the docs should be updated with every release.
In order to perform edits,
    first, edit the `docs/tiddlywiki.info` as follows:

```json
    "plugins": [
        "tiddlywiki/filesystem",
        "tiddlywiki/tiddlyweb"
    ],
```

Then cd into the `docs/` directory
and run `tiddlywiki --listen`.
You can now edit freely in your browser.
Roll back the `tiddlywiki.info` changes,
    commit the rest of your changes,
    and you're set.

*Suggestion for improvement*:
    Provide a way to use a different `tiddlywiki.info`,
    or to automatically remove those plugins on a production build,
    to avoid having to manually change it all the time.


## Bumping the version

1. Update the version number in:
   * `tw-plugin/plugin.info`.
   * The `TiddlyWiki Metadata` tiddler.
   * `util.py` (both the TR compatibility list and the plugin version).
   * The `TiddlyRememberParseable` template.
2. Open and save the `TiddlyRemember` main tiddler
   so that its modification date gets bumped.
3. Quit the TiddlyWiki listener.


## Updating the Anki add-on

1. Update the add-on description in `ankiweb-description.html`,
   including a brief changelog message.
   Don't forget to bump the version number presented.
   Remember that the AnkiWeb description page has *significant whitespace*,
   terribly enough.
2. Run `make` in the root directory.
   This will update `anki-plugin/build.ankiaddon`.
3. Browse to the add-on's page:
   https://ankiweb.net/shared/info/60456529
4. Upload the `build.ankiaddon` file for the latest branch
   and copy and paste the new `ankiweb-description.html` content.
5. Leave this screen open until the remaining steps are ready.


## Publishing to GitHub

1. Commit all doc and release changes made thus far.
2. Check your branch log and make any final rebases or adjustments.
3. Push the branch to GitHub.
4. Create a pull request to `master`.
   If all looks good, complete with a rebase-and-merge and delete the branch.
5. Create a new release on GitHub to publicize the update:
   https://github.com/sobjornstad/TiddlyRemember/releases/new.
   The tag should be in the form `v0.0.0`, using standard semantic versioning.
   Hold off on publishing the release for the moment.


## Publishing the docs and TiddlyWiki plugin

1. Ensure you have a clean working tree.
2. Check out the `master` branch and pull to update from GitHub
   to your just-merged PR.
3. Run `scripts/update-ghpages.sh`
   and follow the directions to push if the update is successful.
4. Browse out to the docs and verify they're updated,
   including the plugin tiddler itself.
   See https://sobjornstad.github.io/TiddlyRemember.
   It can take a minute or two to update a GitHub Pages site;
   refreshing will pick up the changes when they show up.


## Final steps

1. Click the **Update** button on AnkiWeb to update the plugin.
2. Click the **Publish release** button on GitHub to create the release.

## Smoke tests

* Install TW plugin via Node.
* Install TW plugin via drag-and-drop.
* Remove any livelinks to Anki plugin, download/update through Anki interface, and sync up.
