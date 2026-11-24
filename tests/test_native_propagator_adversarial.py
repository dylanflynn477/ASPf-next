from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import clingo

from research.native_backend.propagator import (
    GroundApplication,
    GroundSeed,
    GroundValue,
    NativePropagator,
    ValueKind,
    _EvaluationState,
    _ThreadState,
)


class _RecordingControl:
    """Small callback double for clause-lifecycle tests."""

    thread_id = 0

    def __init__(self) -> None:
        self.clauses: list[tuple[tuple[int, ...], bool]] = []

    def add_clause(
        self,
        clause: Sequence[int],
        *,
        tag: bool = False,
        lock: bool = False,
    ) -> bool:
        del tag
        self.clauses.append((tuple(clause), lock))
        return True

    def propagate(self) -> bool:
        return True


class _FalseAssignment:
    def __init__(self, *false_literals: int) -> None:
        self._false_literals = frozenset(false_literals)

    def is_false(self, literal: int) -> bool:
        return literal in self._false_literals


def test_unlocked_broad_fallback_is_not_remembered_as_a_permanent_clause() -> None:
    propagator = NativePropagator(record_snapshots=False)
    propagator._native_literals = (2, 3)
    state = _ThreadState({2}, {}, {})
    control = _RecordingControl()

    for _ in range(2):
        propagator._block_current_native_assignment(
            cast(clingo.PropagateControl, control),
            state,
            guard=True,
            cause="adversarial-test",
        )

    assert control.clauses == [((-2, 3), False), ((-2, 3), False)]


def test_unassigned_provider_literal_is_never_an_undefinedness_reason() -> None:
    unassigned = NativePropagator._inactive_literal_explanation(2, lambda _literal: False)
    false = NativePropagator._inactive_literal_explanation(2, lambda literal: literal == 2)

    assert unassigned is None
    assert false == frozenset((-2,))


def test_undefinedness_cache_requires_exact_generation_and_false_provider_signature() -> None:
    application = GroundApplication("f", ())
    propagator = NativePropagator(record_snapshots=False)
    propagator._provider_literals = frozenset((2,))
    propagator._potential_applications = frozenset((application,))
    propagator._seeds_by_application = {
        application: (GroundSeed(application, GroundValue(ValueKind.INTEGER, 7), 2),)
    }
    state = _ThreadState(set(), {}, {})
    evaluation = _EvaluationState({}, (), {}, {}, {}, {})

    proved = propagator._cached_dynamic_undefined_explanations(
        evaluation,
        state,
        cast(clingo.Assignment, _FalseAssignment(2)),
    )
    repeated = propagator._cached_dynamic_undefined_explanations(
        evaluation,
        state,
        cast(clingo.Assignment, _FalseAssignment(2)),
    )
    unassigned = propagator._cached_dynamic_undefined_explanations(
        evaluation,
        state,
        cast(clingo.Assignment, _FalseAssignment()),
    )
    state.semantic_generation += 1
    regenerated = propagator._cached_dynamic_undefined_explanations(
        evaluation,
        state,
        cast(clingo.Assignment, _FalseAssignment()),
    )

    assert proved == {application: frozenset((-2,))}
    assert repeated == proved
    assert unassigned == {}
    assert regenerated == {}
    assert propagator.dynamic_undefined_analysis_count == 3
    assert propagator.dynamic_undefined_cache_hit_count == 1
