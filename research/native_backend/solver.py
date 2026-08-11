"""Solve typed research programs through the isolated native propagator."""

from __future__ import annotations

import time
from dataclasses import dataclass

import clingo

from research.native_backend.compiler import compile_program
from research.native_backend.ir import NativeProgram
from research.native_backend.propagator import NativePropagator, NativeWorkMetrics, RuleKey


@dataclass(frozen=True, slots=True)
class NativeModel:
    """Normalized user-visible model reconstructed from a native snapshot."""

    ordinary_atoms: tuple[str, ...]
    assignments: tuple[str, ...]
    undefined_nvariables: tuple[str, ...]

    @property
    def visible(self) -> tuple[str, ...]:
        return tuple(sorted((*self.ordinary_atoms, *self.assignments)))


@dataclass(frozen=True, slots=True)
class NativeReconstructionProfile:
    """Non-overlapping visible-model reconstruction timing components."""

    snapshot_lookup_seconds: float
    symbol_extraction_seconds: float
    ordinary_render_seconds: float
    assignment_render_seconds: float
    undefined_render_seconds: float
    model_storage_seconds: float
    model_sort_seconds: float


@dataclass(frozen=True, slots=True)
class NativeSolveResult:
    """Exhaustive solve result and structural evidence."""

    satisfiable: bool
    models: tuple[NativeModel, ...]
    model_count: int
    models_collected: bool
    internal_source: str
    symbolic_atoms: int
    theory_atoms: int
    statistics_rules: int
    statistics_atoms: int
    statistics_bodies: int
    ground_seconds: float
    solve_seconds: float
    propagator_init_seconds: float
    snapshot_build_seconds: float
    model_reconstruction_seconds: float
    reconstruction_profile: NativeReconstructionProfile | None
    check_count: int
    undo_count: int
    work_metrics: NativeWorkMetrics


def _render_undefined(key: RuleKey, name: str) -> str:
    instance = ",".join(value.render() for value in key.instance)
    suffix = f"[{instance}]" if instance else ""
    return f"{key.identifier}{suffix}:_{name}"


def _private(symbol: clingo.Symbol) -> bool:
    return symbol.type is clingo.SymbolType.Function and symbol.name.startswith("__aspf_")


class NativeSolver:
    """Research-only solver; each call owns independent Clingo and propagator state."""

    def solve(
        self,
        program: NativeProgram,
        *,
        observer: clingo.Observer | None = None,
        model_limit: int = 0,
        collect_models: bool = True,
        profile_reconstruction: bool = False,
    ) -> NativeSolveResult:
        if model_limit < 0:
            raise ValueError("model limit must not be negative")
        source = compile_program(program)
        control = clingo.Control([str(model_limit), "--stats=2", "-t1"])
        propagator = NativePropagator(record_snapshots=collect_models)
        control.register_propagator(propagator)
        if observer is not None:
            control.register_observer(observer)
        control.add("base", [], source)

        ground_started = time.perf_counter()
        control.ground([("base", [])])
        ground_seconds = time.perf_counter() - ground_started
        theory_atom_count = len(list(control.theory_atoms))
        symbolic_atom_count = len(list(control.symbolic_atoms))

        models: list[NativeModel] = []
        model_count = 0
        model_reconstruction_seconds = 0.0
        snapshot_lookup_seconds = 0.0
        symbol_extraction_seconds = 0.0
        ordinary_render_seconds = 0.0
        assignment_render_seconds = 0.0
        undefined_render_seconds = 0.0
        model_storage_seconds = 0.0
        solve_started = time.perf_counter()
        with control.solve(yield_=True) as handle:
            for model in handle:
                model_count += 1
                if not collect_models:
                    continue
                reconstruction_started = time.perf_counter()
                component_started = time.perf_counter()
                snapshot = propagator.snapshot(model.thread_id)
                if profile_reconstruction:
                    snapshot_lookup_seconds += time.perf_counter() - component_started
                    component_started = time.perf_counter()
                symbols = model.symbols(shown=True)
                if profile_reconstruction:
                    symbol_extraction_seconds += time.perf_counter() - component_started
                    component_started = time.perf_counter()
                ordinary = tuple(sorted(str(symbol) for symbol in symbols if not _private(symbol)))
                if profile_reconstruction:
                    ordinary_render_seconds += time.perf_counter() - component_started
                    component_started = time.perf_counter()
                assignments = tuple(
                    f"{application.render()}#={value.render()}"
                    for application, value in snapshot.assignments
                )
                if profile_reconstruction:
                    assignment_render_seconds += time.perf_counter() - component_started
                    component_started = time.perf_counter()
                undefined = tuple(
                    _render_undefined(key, name) for key, name in snapshot.undefined_nvariables
                )
                if profile_reconstruction:
                    undefined_render_seconds += time.perf_counter() - component_started
                    component_started = time.perf_counter()
                models.append(NativeModel(ordinary, assignments, undefined))
                if profile_reconstruction:
                    model_storage_seconds += time.perf_counter() - component_started
                model_reconstruction_seconds += time.perf_counter() - reconstruction_started
        solve_seconds = time.perf_counter() - solve_started
        model_sort_started = time.perf_counter()
        sorted_models = tuple(sorted(models, key=lambda model: model.visible))
        model_sort_seconds = time.perf_counter() - model_sort_started
        reconstruction_profile = None
        if profile_reconstruction:
            reconstruction_profile = NativeReconstructionProfile(
                snapshot_lookup_seconds=snapshot_lookup_seconds,
                symbol_extraction_seconds=symbol_extraction_seconds,
                ordinary_render_seconds=ordinary_render_seconds,
                assignment_render_seconds=assignment_render_seconds,
                undefined_render_seconds=undefined_render_seconds,
                model_storage_seconds=model_storage_seconds,
                model_sort_seconds=model_sort_seconds,
            )

        lp_statistics = control.statistics["problem"]["lp"]
        return NativeSolveResult(
            satisfiable=model_count > 0,
            models=sorted_models,
            model_count=model_count,
            models_collected=collect_models,
            internal_source=source,
            symbolic_atoms=symbolic_atom_count,
            theory_atoms=theory_atom_count,
            statistics_rules=round(lp_statistics["rules"]),
            statistics_atoms=round(lp_statistics["atoms"]),
            statistics_bodies=round(lp_statistics["bodies"]),
            ground_seconds=ground_seconds,
            solve_seconds=solve_seconds,
            propagator_init_seconds=propagator.init_seconds,
            snapshot_build_seconds=propagator.snapshot_build_seconds,
            model_reconstruction_seconds=model_reconstruction_seconds,
            reconstruction_profile=reconstruction_profile,
            check_count=propagator.check_count,
            undo_count=propagator.undo_count,
            work_metrics=propagator.metrics(),
        )
