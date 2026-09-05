# Contributing

Open Framework Commons welcomes corrections, evidence, and proposals that keep
the ecosystem's shared documentation clear without taking authority away from
its independent products.

## Before proposing a change

Read the [Charter](CHARTER.md), [Boundaries](BOUNDARIES.md), and
[Governance](GOVERNANCE.md). A Commons proposal should answer the governance
change test. Product-specific methods, examples, implementation choices, and
research belong in the product that owns them.

Open an issue before a material change. Describe:

- the current problem and who it affects;
- why the concern is shared across every scoped product;
- the evidence, uncertainty, and alternatives;
- the canonical documents that would change; and
- any compatibility or adoption consequences.

Small factual, link, spelling, and formatting corrections may go directly to a
pull request when their scope is obvious.

## Pull requests

Keep changes focused and preserve the distinction between Commons and each
independent product. A pull request should link its issue, explain the decision
being requested, and record the validation performed.

For material changes, include the [evidence disposition](RESEARCH-AND-REVIEW.md#material-change-disposition), [content compatibility assessment](GOVERNANCE.md#content-compatibility), and any relevant [conflict resolution](GOVERNANCE.md#resolving-conflicts). See [worked cases](project/reviews/content-process-cases-2026-09-05.md).

Follow [validation setup and release operations](project/RELEASING.md#validation-setup), then run the repository gate before requesting review:

```sh
./scripts/validate-repository.sh
```

A merged Commons change does not automatically change another product. Each
product separately decides whether to adopt, defer, or deviate from a Commons
release.

## Review and authority

Contributors and reviewers may research, draft, challenge, and recommend. The
founding steward makes Commons decisions under [Governance](GOVERNANCE.md).
Substantive dissent and unresolved limitations should remain visible in the
issue or pull request.

By contributing, you agree that your contribution is licensed under the
repository's [MIT License](LICENSE).
