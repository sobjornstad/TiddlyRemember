Since Anki doesn't have any way to deploy plugins through CD,
    I'm inclined to put off developing a real pipeline
    for the parts I can automate,
    so in the meantime,
    here's at least a consistent set of manual release steps.


## Changing the docs

Aside from straight bugfix releases,
    the docs should be updated with every release.
In order to perform edits:


```bash
cp docs/tiddlywiki.info{,.old}; jq '.plugins = ["tiddlywiki/filesystem", "tiddlywiki/tiddlyweb"]' docs/tiddlywiki.info.old >docs/tiddlywiki.info; cd docs && tiddlywiki --listen
```

This is the automatic version of editing the `docs/tiddlywiki.info` as follows
and running the server so you can edit in your browser:

```json
    "plugins": [
        "tiddlywiki/filesystem",
        "tiddlywiki/tiddlyweb"
    ],
```

Don't stop the listener until you're told to do so by a later step
(or run the snippet again starting from `jq` to get the server restarted if you take a break).

## Bumping the version

1. Open and save the `TiddlyRemember` main tiddler
   so that its modification date gets bumped.
2. Commit your changes as a temp commit
   (unfortunately `bumpversion` refuses to let you leave them uncommitted).
3. Run `bumpversion patch` (or `minor` or `major` if needed).
4. Check and update the `COMPATIBLE_TW_VERSIONS` array
   in `anki-plugin/src/util.py`.
5. Check and update the `compatible-tw5` and `compatible-anki` properties
   in `docs/tiddlers/TiddlyRemember Metadata.json`.
6. Check and update the copyright dates in `LICENSE` and `tw-plugin/license.tid`.


## Updating the Anki add-on

1. Update the add-on description in `ankiweb-description.html`,
   including a brief changelog message and the release date.
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

1. Quit the TiddlyWiki listener (hit Ctrl+C on the big PasteOps command from above).
   Run `cd -; mv docs/tiddlywiki.info.old docs/tiddlywiki.info` to restore the file.
2. `git reset --soft HEAD^` to go back to before the last temp commit.
3. Commit all doc and release changes made thus far, this time for real.
4. Check your branch log and make any final rebases or adjustments.
5. Push the branch to GitHub.
6. Create a pull request to `master`.
   If all looks good, complete with a rebase-and-merge and delete the branch.
7. Create a new release on GitHub to publicize the update:
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

1. Click the **Save** button on AnkiWeb to update the plugin.
2. Click the **Publish release** button on GitHub to create the release.

## Smoke tests

* Install TW plugin via Node: 
      1. `cd ~/cabinet/Me/Records/m2`.
      2. `vim peru.yaml` and confirm that the version of TiddlyRemember that's active
         is cloned from the GitHub repo.
      3. `peru reup tiddlyremember`.
      4. Restart the M2 server. Verify the new version number in More > Plugins > TR.
* Install TW plugin via drag-and-drop to a file wiki (e.g., tiddlywiki.com)
  and verify version number.
* Try syncing:
  1. `cd ~/.local/share/Anki2/addons21`.
  2. `ls -l` and check if the plugin is livelinked. Remove livelink if needed.
  3. Launch Anki and run "Check for Updates" in the addon settings.
     Verify update is available, install and relaunch.
  4. Run a sync, verify success.
