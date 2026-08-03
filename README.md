# Open Framework Commons

Open Framework Commons is the small set of shared principles and boundaries for Brad Groux's Open Framework Ecosystem.

This release is scoped to exactly four independent products:

- AI-Native Operating Framework
- Influence Operating Framework
- AI Dev Days
- Relationship Operating Framework, when it is created

Commons is documentation. People and agents can read it before using or changing an ecosystem product so they understand the philosophy those products share.

Commons is not a framework for accomplishing product-specific work. It is not an operating system, application, runtime, compatibility layer, certification, shared data model, or parent product.

## Ecosystem at a glance

This diagram answers how four independent products can share Commons without becoming modules of it.

```mermaid
flowchart TB
  subgraph products["Independent products — equal provenance"]
    direction LR
    native["AI-Native<br/>Operating Framework"]
    influence["Influence<br/>Operating Framework"]
    devdays["AI Dev Days<br/>Learning community"]
    relationship["Relationship<br/>Operating Framework<br/>(future)"]

    native ~~~ influence
    influence ~~~ devdays
    devdays ~~~ relationship
  end

  commons["Open Framework Commons<br/>Shared principles and boundaries"]

  products -. "all are in Commons scope" .-> commons
```

Commons supplies shared documentation beneath the products. It does not direct or rank them. Each existing product separately decides whether and when to adopt an exact Commons release; the future Relationship Operating Framework will make that decision when it exists.

## Read this first

1. [Charter](CHARTER.md) — purpose and authority
2. [Principles](PRINCIPLES.md) — ideas every product shares
3. [Boundaries](BOUNDARIES.md) — what stays shared and what stays local
4. [Research and review](RESEARCH-AND-REVIEW.md) — how claims and learning remain honest
5. [Governance](GOVERNANCE.md) — how shared documentation changes
6. [Context](CONTEXT.md) — the vocabulary used here

## How people and agents should use Commons

Read Commons for the shared philosophy, then read the selected product for the actual method, examples, and task guidance. If the two appear to conflict, stop and surface the conflict rather than silently rewriting either one.

Each product stands alone. A person may use one product without adopting the others.

## Independent review record

Sanitized independent reviews and their disposition are published in [project/reviews](project/reviews/README.md). Each report identifies the exact commit reviewed and its limitations. Document review does not establish adoption or real-world effectiveness.

## Status

Version 1.0.0 is the approved initial release at commit `27870fb1d57d951b9ef5a3a86f33ef068ee557da`.

The three existing ecosystem products have adopted that exact release:

- [AI-Native Operating Framework](https://github.com/BradGroux/ai-native-operating-framework/blob/2e402d89598849f37e12f6e54c9d7f24ac5ca76c/decisions/0008-adopt-open-framework-commons-v1-0-0.md);
- [Influence Operating Framework](https://github.com/BradGroux/influence-operating-framework/blob/f91851a1b42b28b01928e5db7aaac4c20b946417/decisions/0003-adopt-open-framework-commons-v1.0.0.md); and
- [AI Dev Days](https://github.com/BradGroux/ai-dev-days/blob/04d9bad2588af2e7725fbdb3d03f232373dcd620/decisions/0002-adopt-open-framework-commons-v1.0.0.md).

Relationship Operating Framework has not been created and therefore has not made an adoption decision.
