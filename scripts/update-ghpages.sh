#!/bin/bash

die() {
    ret=$?
    printf "%s\\n" "$@" >&2
    exit $ret
}

tmp_location="/tmp/build-tiddlyremember"
pages_branch="gh-pages"

# Precondition check.
git diff-index --quiet HEAD || die "Working directory is dirty. Please commit changes before continuing."
[ -d "docs" ] || die "Please run this script from the project root."
#[ "$(git rev-parse --abbrev-ref HEAD)" = "master" ] || die "Please merge your changes to and check out master before publishing to Pages."
git rev-parse "$pages_branch" >/dev/null 2>/dev/null || die "The gh-pages branch does not exist."

# Ensure built copy is up to date.
make
revision=$(git rev-parse HEAD)

rm -rf "$tmp_location"
git worktree add "$tmp_location" "$pages_branch"
cp -r docs/output/* "$tmp_location"
(
    cd "$tmp_location" || die "Failed to cd to just-created temporary location!"
    git add .
    git commit -am "updating GitHub Pages branch with docs built from $revision"
)
rm -rf "$tmp_location"
git worktree prune

echo "If all looks good, now run 'git push origin gh-pages'" to publish.
