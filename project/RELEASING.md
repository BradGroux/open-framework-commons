# Validation and release operations

This is Commons repository stewardship, not a required workflow or toolchain for ecosystem products. Content decisions come first: [compatibility](../GOVERNANCE.md#content-compatibility), [evidence](../RESEARCH-AND-REVIEW.md#material-change-disposition), and [conflict resolution](../GOVERNANCE.md#resolving-conflicts). The steward approves substantive meaning and publication; a green check does not supply that authority.

## Validation setup

Use Git, Bash 3.2 or newer, Python 3.12, Node 22 or newer, Chrome and Gitleaks 8.30.1. GitHub CLI is needed only for release verification/publication. Ruby and ripgrep are no longer gate dependencies: the former regex parser and conditional scanner have been replaced. Install tools explicitly; validation never downloads them automatically.

From this checkout:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-validation.txt
npm ci --ignore-scripts
```

Python dependencies and Mermaid CLI are development-only. Python transitive versions and hashes are fixed in `requirements-validation.txt`; npm uses `package-lock.json`. Chrome is a maintained host tool; CI supplies its installed browser. Set `CHROME_PATH` if needed. On macOS the default is the standard Google Chrome application.

Stage intended new public files before validation. The contribution gate reads working copies of index-listed files so edits to existing files are checked immediately. An unstaged/untracked link target is not publishable. Ignored recovery archives never satisfy a public link. Unstage or remove an intended deletion from the index before validating; preserve unrelated work.

```sh
./scripts/validate-repository.sh
.venv/bin/python scripts/validate.py diagrams
gitleaks git . --no-banner --redact --log-level error
```

The root gate runs shell syntax, isolated unit regressions, calendar/date and CFF schema validation, public-inventory Markdown links and anchors, scoped-product checks, publication policy and a redacted Gitleaks scan of a temporary copy of every publishable file. No scanner error is a clean result. Diagnostics identify files/checks without echoing sensitive match values. Release verification requires a clean tree and committed inventory.

Markdown uses CommonMark parsing with tables and strikethrough. Inline/reference links, titles, code exclusions, local fragments, percent-encoded paths and duplicate-heading IDs are supported. Local targets must be regular public files within the repository; symlinks, raw HTML navigation and directory-only links are unsupported. Heading IDs support ordinary Unicode letters/numbers/marks, inline emphasis/code, spaces, underscores and hyphens; avoid embedded HTML or exotic symbols in linked headings. External URL availability is checked during relevant content review, not by every offline gate.

Diagrams are compiled separately to `.validation-render/`; compilation tests syntax. Visually inspect diagrams when meaning or layout changes. Fictional scenario assessment and product applicability review remain human content gates; neither CI nor diagram rendering proves effectiveness in practice.

## Tool maintenance

Dependabot proposes monthly action and npm updates; retain immutable action SHAs. Monthly, and before a release, review Python and Gitleaks updates and advisories. To refresh Python dependencies, review `requirements-validation.in`, regenerate with `uv pip compile requirements-validation.in --generate-hashes -o requirements-validation.txt`, and rerun all gates. Update the Gitleaks version in the validator and workflow together, verify the release archive checksum, and update this document. Do not auto-merge dependency changes. Browser/platform updates can affect rendering, so inspect changed output rather than asserting pixel-identical reproducibility.

Publication policy exceptions in `scripts/publication-policy.json` name an exact file and SHA-256 of one literal line. They permit regex definitions only; no directory is exempt, and Gitleaks still scans every file including that policy. Any new exception requires review of why the literal is necessary. Never add a credential value as an exception.

## Prepare a release

1. Record substantive change/adoption consequences under Governance and the linked issue/decision. Do not require simultaneous downstream adoption. The date is an identifier, not a compatibility promise.
2. Choose the actual UTC publication date: `YYYY.MM.DD`, with `.1`, `.2` for additional same-day editions. If publication slips to another UTC date, update metadata before tagging. Existing v1.0.0/v1.1.0 releases remain unchanged; never add dated aliases.
3. Update `VERSION`, README, Charter, `CITATION.cff`, the changelog and `project/releases/v<VERSION>.md`. Quote the calendar version in CFF; its date uses `YYYY-MM-DD`. Release notes identify the predecessor, compatibility, adoption consequences, limits and verification.
4. Stage only intended changes, run all gates and review the diff, source scenarios, diagrams and historical preservation. Use a focused PR linked to the issues. Require the `validate` status before merging. A solo steward is not required to approve their own PR.
5. Merge, then validate the clean merged main with the same gates. Confirm the remote commit and local HEAD agree. Never publish a tag on a pre-merge candidate.

## Publish and verify

Run authenticated GitHub commands as BradGroux and confirm identity before writes. The example shell variables derive from the reviewed metadata; this sequence creates one annotated tag and its release, without force flags:

```sh
gh auth status --hostname github.com
test "$(gh api --hostname github.com user --jq .login)" = BradGroux
edition="$(cat VERSION)"
release_tag="v$edition"
git tag -a "$release_tag" -m "Open Framework Commons $release_tag"
git push origin "refs/tags/$release_tag"
gh release create "$release_tag" --repo BradGroux/open-framework-commons --verify-tag --title "Open Framework Commons $release_tag" --notes-file "project/releases/$release_tag.md"
./scripts/validate-release.sh "$release_tag"
```

Prepare all intended assets and content before final publication; future releases use GitHub release immutability. No downloadable assets are required for this documentation edition. Read back the published author, tag/commit, final flags and body. The verifier always addresses `github.com/BradGroux/open-framework-commons`, ignores ambient repository selection, and compares the committed note with the API body. Only CRLF versus LF and trailing newlines are normalized. Substantive text differences fail.

## Historical verification and recovery

Run the current verifier with an older tag, for example `./scripts/validate-release.sh v1.1.0`, from a clean checkout with its validation environment. It compares the annotated local/remote objects and peeled commit, available VERSION, author, final state and committed release notes. v1.0.0 predates a committed release-note file and VERSION: the verifier explicitly reports that body comparison is unavailable. It does not rewrite history or claim historical validation by checks that did not exist then.

If a check fails, stop publication or adoption and record the mismatch. Do not force a tag or delete/recreate a release. Correct published guidance through a new dated edition (same-day suffix when appropriate), explain the correction and preserve the earlier identity. Products independently review the new edition. A failed publication attempt without a public release requires inspection of the existing tag and remote state before retrying; reuse only the identical reviewed tag, never substitute a commit.

## Repository protections

The published-version tag ruleset prevents updates and deletion without bypass actors while permitting new tag creation. Release immutability protects future published editions. Main requires a PR and the `validate` check and forbids force-push/deletion. No extra reviewer or self-approval requirement is imposed. There is no standing emergency bypass; a steward must explicitly document any necessary temporary policy change and restore it, rather than silently overriding a failed check. Verify live settings through the API; source documentation alone is not enforcement.

Repository protections are Commons-local and do not alter another product’s release policy or adoption authority.
