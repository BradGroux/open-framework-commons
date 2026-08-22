#!/usr/bin/env bash
set -euo pipefail

repository_root="$(git rev-parse --show-toplevel)"
cd "$repository_root"

required_files=(
  README.md CHARTER.md PRINCIPLES.md BOUNDARIES.md GOVERNANCE.md
  RESEARCH-AND-REVIEW.md CONTEXT.md LICENSE VERSION CHANGELOG.md
  CITATION.cff CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md
  decisions/0001-recognize-focus-operating-framework.md
  project/releases/v1.1.0.md
)

for required_file in "${required_files[@]}"; do
  test -f "$required_file" || { echo "Missing required file: $required_file" >&2; exit 1; }
done

version="$(tr -d '\r\n' < VERSION)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "VERSION is not semantic: $version" >&2; exit 1; }

grep -Fq "Version $version" README.md
grep -Fq "Version $version" CHARTER.md
grep -Fq "## [$version]" CHANGELOG.md
grep -Fq "version: $version" CITATION.cff

scoped_products=(
  "AI-Native Operating Framework"
  "Influence Operating Framework"
  "AI Dev Days"
  "Relationship Operating Framework"
  "Focus Operating Framework"
)

for canonical_file in README.md CHARTER.md BOUNDARIES.md CONTEXT.md GOVERNANCE.md; do
  for scoped_product in "${scoped_products[@]}"; do
    grep -Fq "$scoped_product" "$canonical_file" || {
      echo "Missing $scoped_product scope reference: $canonical_file" >&2
      exit 1
    }
  done
done

grep -Fq "exactly five independent products" README.md

if rg -n "all four|exactly four|four ecosystem products|effects on all four|apply to all four" \
  README.md CHARTER.md BOUNDARIES.md CONTEXT.md GOVERNANCE.md; then
  echo "Obsolete four-product scope language remains in a canonical document." >&2
  exit 1
fi

grep -Fq 'a0f0d384e9010a65d1a21a324b4c912433d5e031' project/reviews/README.md
grep -Fq '7c41e29ef7bcebc7c7994951fe786a910aa26658' project/reviews/README.md

ruby -r date -r yaml -e '
  data = YAML.safe_load(File.read("CITATION.cff"), permitted_classes: [Date], aliases: false)
  abort("CITATION.cff version mismatch") unless data["version"].to_s == File.read("VERSION").strip
  abort("CITATION.cff release date missing") unless data["date-released"]
'

ruby scripts/validate-markdown.rb

if rg --hidden -n -i '/Users/|gho_[[:alnum:]_]+|sk-[[:alnum:]_-]+|codex|chatgpt|claude|anthropic|openai' \
  --glob '!archive/**' --glob '!project/reviews/**' \
  --glob '!.git/**' \
  --glob '!scripts/validate-repository.sh' .; then
  echo "Publication-hygiene pattern found in current public content." >&2
  exit 1
fi

empty_tree="$(git hash-object -t tree /dev/null)"
git diff --check "$empty_tree" HEAD
git diff --check HEAD

echo "Repository validation passed for version $version."
