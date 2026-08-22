from __future__ import annotations

from collections.abc import Sequence

from research.native_backend.propagator import NativePropagator, _ThreadState


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


def test_unlocked_broad_fallback_is_not_remembered_as_a_permanent_clause() -> None:
    propagator = NativePropagator(record_snapshots=False)
    propagator._native_literals = (2, 3)
    state = _ThreadState({2}, {}, {})
    control = _RecordingControl()

    for _ in range(2):
        propagator._block_current_native_assignment(  # type: ignore[arg-type]
            control,
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
