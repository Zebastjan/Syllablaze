# Documentation Archive

This directory contains temporary documentation from the Syllablaze development process. Files are retained for historical reference and are not part of the active documentation.

## Archive Structure

### refactoring/
Contains 29 phase-by-phase refactoring documents from the major architecture refactoring (Feb 2026). Key design decisions have been extracted to ADRs in `docs/adr/`.

**Retention policy:** Review quarterly, delete files older than 6 months.

### implementation-summaries/
Contains 7 implementation summary documents including faster-whisper migration, bridge consolidation, and recording dialog cleanup.

**Key content extracted to:**
- `docs/explanation/design-decisions.md`
- `docs/adr/0001-manager-pattern.md`

### migrations/
Contains 2 migration guides (Kirigami UI migration, status tracking).

**Key content extracted to:**
- `docs/adr/0002-qml-kirigami-ui.md`
- `docs/developer-guide/patterns-and-pitfalls.md`

### verification/
Contains verification documents from feature implementations.

### plans/
Contains 11 planning documents, context files, and feature proposals.

**Retention policy:** Delete after implementation completion and ADR creation.

### reports/
Contains 2 comprehensive reports (refactoring report, async/sync best practices).

**Key content extracted to:**
- `docs/adr/0001-manager-pattern.md`
- `docs/explanation/design-decisions.md`

## Quarterly Review Process

1. Check file age: `find docs/archive -name "*.md" -mtime +180`
2. Verify content has been extracted to active docs
3. Delete files older than 6 months
4. Update this README with deletion summary

## Last Review

**Date:** 2026-02-19
**Action:** Initial archive creation
**Files archived:** 51 total documents
