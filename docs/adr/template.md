# ADR-XXXX: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded]
**Date:** YYYY-MM-DD
**Deciders:** [Agent | Developer | Team]

## Context

What problem needs solving? What constraints exist? What is the background situation that led to this decision?

- Describe the forces at play (technical, political, social, project constraints)
- Include relevant requirements or goals
- Reference related issues, discussions, or prior decisions

## Decision

What approach did we adopt? How is it implemented?

- State the decision clearly and concisely
- Explain the chosen solution
- Describe key implementation details
- Include code examples or diagrams if helpful

## Consequences

### Positive

Benefits and problems solved:
- List advantages gained
- Problems addressed by this decision
- Improvements to codebase quality or maintainability

### Negative

Trade-offs and new complexity:
- List disadvantages or costs
- New complexity introduced
- Technical debt created (if any)

### Neutral

Other changes that are neither clearly positive nor negative:
- Side effects
- Scope changes
- Areas requiring future attention

## Alternatives Considered

### Alternative 1: [Name]

- **Description:** Brief explanation of alternative approach
- **Pros:** Advantages
- **Cons:** Disadvantages
- **Reason for rejection:** Why this was not chosen

### Alternative 2: [Name]

- **Description:** Brief explanation of alternative approach
- **Pros:** Advantages
- **Cons:** Disadvantages
- **Reason for rejection:** Why this was not chosen

## References

- **Code:** `path/to/implementation.py` (main implementation)
- **Documentation:** Link to related explanation docs
- **Issues:** GitHub issue numbers
- **External:** Links to external resources (articles, libraries, specs)
- **Related ADRs:** Links to ADRs that supersede or are superseded by this one

---

## Template Usage Notes

**When to create an ADR:**
- Significant architectural changes
- Choosing between competing approaches
- Establishing new patterns or conventions
- Platform-specific workarounds with architectural impact
- Decisions that affect multiple components

**Numbering:**
- Use 4-digit zero-padded format: `0001`, `0002`, etc.
- Number sequentially based on creation order
- Don't reuse numbers

**Status values:**
- **Proposed:** Decision is under discussion
- **Accepted:** Decision is approved and implemented
- **Deprecated:** Decision is no longer recommended (but not replaced)
- **Superseded:** Decision has been replaced (link to new ADR)

**Deciders:**
- **Agent:** Decision made by AI agent (Claude Code)
- **Developer:** Decision made by human developer
- **Team:** Collaborative decision

**Best practices:**
- Keep ADRs focused on a single decision
- Write in past tense (decision has been made)
- Be concise but complete
- Update status as decision evolves
- Link from code comments where decision is implemented
