"""Measure why an ordinary relation join is not historical n-variable support."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

import clingo


class GroundCounter(clingo.Observer):
    """Count ordinary rules emitted by Clingo's grounder."""

    def __init__(self) -> None:
        self.rules = 0

    def rule(self, choice: bool, head: Sequence[int], body: Sequence[int]) -> None:
        del choice, head, body
        self.rules += 1


@dataclass(frozen=True, slots=True)
class GroundSize:
    """Observable size of one grounded probe program."""

    rules: int
    atoms: int


def _source(size: int, *, copy_rule: str = "") -> str:
    return f"dom(1..{size}).\n1 {{ probe_value(f(x),X) : dom(X) }} 1.\n{copy_rule}"


def _ground_size(size: int, *, copy_rule: str = "") -> GroundSize:
    control = clingo.Control(["0"])
    observer = GroundCounter()
    control.register_observer(observer)
    control.add("base", [], _source(size, copy_rule=copy_rule))
    control.ground([("base", [])])
    return GroundSize(observer.rules, len(list(control.symbolic_atoms)))


def _copy_model_counts(size: int, *, copy_rule: str) -> tuple[int, int]:
    control = clingo.Control(["0"])
    control.add("base", [], _source(size, copy_rule=copy_rule))
    control.ground([("base", [])])

    model_count = 0
    copied_count = 0
    with control.solve(yield_=True) as handle:
        for model in handle:
            model_count += 1
            values: dict[str, clingo.Symbol] = {}
            for symbol in model.symbols(atoms=True):
                if symbol.type is not clingo.SymbolType.Function or symbol.name != "probe_value":
                    continue
                values[str(symbol.arguments[0])] = symbol.arguments[1]
            if values.get("f(x)") == values.get("f(y)"):
                copied_count += 1
    return model_count, copied_count


def run(sizes: Sequence[int]) -> None:
    """Print grounding growth and simple semantic checks for candidate rewrites."""

    relation_copy = "probe_value(f(y),V) :- probe_value(f(x),V).\n"
    fake_placeholder = "probe_value(f(y),nvar_placeholder) :- probe_value(f(x),nvar_placeholder).\n"

    print(
        "domain,baseline_rules,relation_rules,added_rules,baseline_atoms,relation_atoms,added_atoms"
    )
    for size in sizes:
        baseline = _ground_size(size)
        relation = _ground_size(size, copy_rule=relation_copy)
        print(
            f"{size},{baseline.rules},{relation.rules},{relation.rules - baseline.rules},"
            f"{baseline.atoms},{relation.atoms},{relation.atoms - baseline.atoms}"
        )

    semantic_size = min(sizes)
    models, copied = _copy_model_counts(semantic_size, copy_rule=relation_copy)
    fake_models, fake_copied = _copy_model_counts(semantic_size, copy_rule=fake_placeholder)
    print(f"relation-copy model check: {copied}/{models} copied")
    print(f"fake-placeholder model check: {fake_copied}/{fake_models} copied")
    print(
        "result: the relation rewrite matches the simple copy models but adds one grounded "
        "rule and atom per candidate value; it is not grounder-inert n-variable support"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[4, 16, 64],
        help="positive value-domain sizes to measure",
    )
    arguments = parser.parse_args()
    if any(size < 1 for size in arguments.sizes):
        parser.error("every domain size must be positive")
    run(arguments.sizes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
