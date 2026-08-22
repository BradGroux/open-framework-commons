#!/usr/bin/env bash
set -euo pipefail

repository_root="$(git rev-parse --show-toplevel)"
cd "$repository_root"

./scripts/validate-repository.sh

version="$(tr -d '\r\n' < VERSION)"
expected_tag="v$version"
release_tag="${1:-$expected_tag}"

test "$release_tag" = "$expected_tag" || {
  echo "Release tag $release_tag does not match VERSION $version." >&2
  exit 1
}

git rev-parse -q --verify "refs/tags/$release_tag^{tag}" >/dev/null || {
  echo "Missing annotated tag: $release_tag" >&2
  exit 1
}

head_commit="$(git rev-parse HEAD)"
tag_commit="$(git rev-parse "$release_tag^{commit}")"
test "$tag_commit" = "$head_commit" || {
  echo "Tag $release_tag peels to $tag_commit, not HEAD $head_commit." >&2
  exit 1
}

test -z "$(git status --porcelain)" || {
  echo "Working tree is not clean." >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || {
  echo "GitHub CLI is required for public release verification." >&2
  exit 1
}

github_login="$(gh api user --jq .login)"
test "$github_login" = "BradGroux" || {
  echo "GitHub identity is $github_login, expected BradGroux." >&2
  exit 1
}

remote_tag_object="$(gh api "repos/BradGroux/open-framework-commons/git/ref/tags/$release_tag" --jq .object.sha)"
local_tag_object="$(git rev-parse "refs/tags/$release_tag")"
test "$remote_tag_object" = "$local_tag_object" || {
  echo "Remote tag object $remote_tag_object does not match local tag object $local_tag_object." >&2
  exit 1
}

remote_tag_commit="$(gh api "repos/BradGroux/open-framework-commons/git/tags/$remote_tag_object" --jq .object.sha)"
test "$remote_tag_commit" = "$head_commit" || {
  echo "Remote tag peels to $remote_tag_commit, not HEAD $head_commit." >&2
  exit 1
}

release_state="$(gh release view "$release_tag" --json tagName,isDraft,isPrerelease --jq \
  '[.tagName, .isDraft, .isPrerelease] | @tsv')"
test "$release_state" = "$release_tag"$'\tfalse\tfalse' || {
  echo "Published release state is invalid: $release_state" >&2
  exit 1
}

echo "Release validation passed for $release_tag at $head_commit."
