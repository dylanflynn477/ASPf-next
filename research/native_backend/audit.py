"""Opt-in clause records for auditing the research propagator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ClauseAuditKind(StrEnum):
    """Semantic reasons that can cause the research propagator to add a clause."""

    SEED_FUNCTIONALITY = "seed-functionality"
    DERIVED_FUNCTIONALITY = "derived-functionality"
    GUARD = "guard"
    BROAD_FALLBACK = "broad-fallback"


@dataclass(frozen=True, slots=True)
class SupportOrigin:
    """One true signed literal and the native metadata represented by its sign."""

    literal: int
    descriptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClauseAudit:
    """A research-only account of one added solver clause.

    ``support_literals`` contains only signed literals known true and used as the
    semantic antecedent of a narrow explanation.  Broad fallbacks intentionally leave
    it empty because their completion clauses can contain currently unassigned
    literals and must not be presented as positive evidence.

    Records are deterministic in the supported one-thread audit mode.  Their order in
    a two-thread exploratory solve follows Clingo's callback schedule.
    """

    sequence: int
    thread_id: int
    kind: ClauseAuditKind
    target: str
    support_literals: tuple[int, ...]
    support_origins: tuple[SupportOrigin, ...]
    required_literal: int | None
    clause: tuple[int, ...]
    early: bool
    locked: bool
