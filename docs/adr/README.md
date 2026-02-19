# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant design decisions in Syllablaze.

## What is an ADR?

An ADR is a document that captures an important architectural decision along with its context and consequences. ADRs help:

- Understand why the codebase is structured the way it is
- Onboard new contributors by explaining design rationale
- Avoid revisiting settled decisions
- Document trade-offs and alternatives considered
- Guide AI agents working on the codebase

## ADR Index

| Number | Title | Status | Date | Deciders |
|--------|-------|--------|------|----------|
| [0001](0001-manager-pattern.md) | Manager Pattern for Component Organization | Accepted | 2026-02-19 | Agent + Developer |
| [0002](0002-qml-kirigami-ui.md) | QML UI with Kirigami Framework | Accepted | 2026-02-19 | Developer |
| [0003](0003-settings-coordinator.md) | Settings Coordinator Pattern | Accepted | 2026-02-19 | Agent + Developer |

## Creating a New ADR

1. **Copy the template:**
   ```bash
   cp docs/adr/template.md docs/adr/XXXX-title.md
   ```

2. **Number sequentially:**
   Use the next available 4-digit number (0001, 0002, etc.)

3. **Fill all sections:**
   - Context: Why is this decision needed?
   - Decision: What did we choose?
   - Consequences: What are the effects?
   - Alternatives: What else did we consider?
   - References: Links to code and docs

4. **Update this index:**
   Add entry to the table above

5. **Link from related docs:**
   Reference the ADR from relevant explanation docs or code comments

6. **Add to MkDocs navigation:**
   Update `mkdocs.yml` to include new ADR

## When to Create an ADR

Create an ADR when making decisions about:

- **Architecture:** New managers, coordinators, or major refactoring
- **Technology choices:** Selecting frameworks, libraries, or platforms
- **Patterns:** Establishing coding patterns or conventions
- **Trade-offs:** Choosing between competing approaches with significant implications
- **Platform workarounds:** Wayland-specific solutions or OS-specific behavior
- **API design:** Public interfaces or inter-component communication protocols

## Status Lifecycle

```
Proposed → Accepted → (Deprecated or Superseded)
```

- **Proposed:** Under discussion, not yet implemented
- **Accepted:** Approved and implemented in codebase
- **Deprecated:** No longer recommended, but not replaced
- **Superseded:** Replaced by newer ADR (link to replacement)

## Best Practices

- **Write concisely:** ADRs should be readable in 5-10 minutes
- **Focus on "why":** Explain rationale, not just "what"
- **Document alternatives:** Show what was considered and rejected
- **Link to code:** Reference implementation files
- **Update status:** Mark as Deprecated/Superseded when appropriate
- **Review quarterly:** Ensure ADRs reflect current reality

## Template

See [template.md](template.md) for the ADR template with detailed usage notes.

## Related Documentation

- [Design Decisions](../explanation/design-decisions.md) - High-level design rationale consolidated from ADRs
- [Settings Architecture](../explanation/settings-architecture.md) - Detailed settings derivation (see ADR 0003)
- [Patterns & Pitfalls](../developer-guide/patterns-and-pitfalls.md) - Qt/PyQt6 best practices
