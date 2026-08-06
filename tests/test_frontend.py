from __future__ import annotations

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program
from aspf_next.ir import AspfStatement, NAtomRole, OrdinaryStatement


def test_parses_declaration_and_basic_assignment() -> None:
    program = parse_program("#nherb balance/1.\nbalance(account1) #= 500.\n", filename="basic.aspf")

    assert [(item.name, item.arity) for item in program.declarations] == [("balance", 1)]
    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].application.render() == "balance(account1)"
    assert statement.n_atoms[0].value.text == "500"
    assert statement.n_atoms[0].role is NAtomRole.HEAD


def test_parses_positive_body_comparison_and_multiline_rule() -> None:
    program = parse_program(
        """#nherb balance/1.
solvent(account1) :-
    account(account1),
    balance(account1) #= 500.
""",
        filename="multiline.aspf",
    )

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].role is NAtomRole.BODY
    assert statement.n_atoms[0].span.start < statement.n_atoms[0].span.end


def test_preserves_ordinary_statement_text() -> None:
    text = '% keep #= inert\nmessage("literal #= text").\np(X) :- q(X).\n'
    program = parse_program(text)

    executable = [statement for statement in program.statements if statement.text.strip()]
    assert len(executable) == 2
    assert all(isinstance(statement, OrdinaryStatement) for statement in executable)
    assert "".join(statement.text for statement in program.statements) == text


def test_comments_do_not_break_statement_scanning() -> None:
    text = """#nherb balance/1.
% a period. and #>= are comments
balance(
  account1 % an argument comment
) #= 500. % trailing.
"""
    program = parse_program(text, filename="comments.aspf")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].application.arguments[0].text == "account1"


@pytest.mark.parametrize(
    ("source", "line", "column"),
    [
        ("__aspf_value(key,value).\n", 1, 1),
        ("ordinary.\np(__aspf_private).\n", 2, 3),
    ],
)
def test_rejects_user_identifiers_in_reserved_internal_namespace(
    source: str, line: int, column: int
) -> None:
    with pytest.raises(UnsupportedSyntaxError, match="reserved for aspf-next internals") as caught:
        parse_program(source, filename="reserved.aspf")

    assert caught.value.location.line == line
    assert caught.value.location.column == column


def test_reserved_identifier_text_in_comments_and_strings_is_inert() -> None:
    program = parse_program('% __aspf_comment.\nmessage("__aspf_string").\n')

    assert len(program.statements) == 2


@pytest.mark.parametrize(
    ("source", "column"),
    [
        ("#nherb balance/1.\nbalance(account1).\n", 1),
        ("#nherb balance/1.\np(balance(account1)).\n", 3),
    ],
)
def test_rejects_declared_non_herbrand_symbol_outside_n_atom(source: str, column: int) -> None:
    with pytest.raises(UnsupportedSyntaxError, match="may only be used as the key") as caught:
        parse_program(source, filename="misuse.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == column


def test_rejects_declared_symbol_outside_n_atom_in_mixed_rule() -> None:
    source = "#nherb balance/1.\np(balance(a)) :- balance(a) #= 1.\n"

    with pytest.raises(UnsupportedSyntaxError, match="may only be used as the key") as caught:
        parse_program(source, filename="mixed.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == 3


def test_declared_symbol_text_in_comments_and_strings_is_inert() -> None:
    program = parse_program('#nherb balance/1.\nlabel("balance"). % balance(a).\n')

    assert len(program.declarations) == 1


def test_rejects_declared_zero_arity_symbol_as_n_atom_value() -> None:
    source = "#nherb mode/0.\n#nherb status/1.\nstatus(alice) #= mode.\n"

    with pytest.raises(UnsupportedSyntaxError, match="may only be used as the key") as caught:
        parse_program(source, filename="value.aspf")

    assert caught.value.location.line == 3
    assert caught.value.location.column == 18


def test_rejects_declared_zero_arity_symbol_as_n_atom_argument() -> None:
    source = "#nherb current/0.\n#nherb reading/1.\nreading(current) #= active.\n"

    with pytest.raises(UnsupportedSyntaxError, match="may only be used as the key") as caught:
        parse_program(source, filename="argument.aspf")

    assert caught.value.location.line == 3
    assert caught.value.location.column == 9


def test_allows_declared_names_only_as_n_atom_keys() -> None:
    source = """#nherb mode/0.
#nherb left/1.
#nherb right/1.
mode #= active.
left(a) #= 1.
right(b) #= 2.
ok :- left(a) #= 1, right(b) #= 2.
label("mode"). % mode left(a) right(b).
"""

    program = parse_program(source)
    n_atom_count = sum(
        len(statement.n_atoms)
        for statement in program.statements
        if isinstance(statement, AspfStatement)
    )

    assert n_atom_count == 5


@pytest.mark.parametrize("operator", ["#!=", "#<", "#<=", "#>", "#>="])
def test_each_unsupported_operator_has_location(operator: str) -> None:
    text = f"#nherb balance/1.\nokay :- balance(account1) {operator} 500.\n"

    with pytest.raises(UnsupportedSyntaxError) as caught:
        parse_program(text, filename="operators.aspf")

    assert str(caught.value).startswith("operators.aspf:2:")
    assert operator in str(caught.value)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("#nherb.\n", "global '#nherb.'"),
        ("#show #nherb.\n", "legacy '#show #nherb'"),
        (
            "#nherb balance/1.\np :- not balance(account1) #= 500.\n",
            "default-negated n-atoms",
        ),
        (
            "#nherb balance/1.\np :- #count { X : balance(account1) #= 500 } > 0.\n",
            "aggregates or choice",
        ),
        (
            "#nherb balance/1.\nbalance(X) #= 500.\n",
            "variables",
        ),
        (
            "#nherb balance/1.\nbalance(account1) #= 500 + 1.\n",
            "arithmetic",
        ),
        (
            "#nherb first/1.\n#nherb second/1.\nfirst(a) #= second(a).\n",
            "cannot be used as the value",
        ),
        (
            "#nherb first/1.\nfirst(a) #= ordinary(value).\n",
            "only integer, symbolic constant, and string values",
        ),
    ],
)
def test_explicitly_unsupported_constructs_are_diagnostic(source: str, message: str) -> None:
    with pytest.raises(UnsupportedSyntaxError, match=message) as caught:
        parse_program(source, filename="unsupported.aspf")

    assert caught.value.location.filename == "unsupported.aspf"
    assert caught.value.location.line >= 1
    assert caught.value.location.column >= 1


def test_rejects_undeclared_and_wrong_arity_applications() -> None:
    with pytest.raises(UnsupportedSyntaxError, match="not declared"):
        parse_program("missing(a) #= 1.")

    with pytest.raises(UnsupportedSyntaxError, match="expects 2 argument"):
        parse_program("#nherb pair/2.\npair(a) #= yes.")


def test_accepts_integer_symbol_string_and_ordinary_ground_function_terms() -> None:
    program = parse_program('#nherb item/2.\nitem(product(7),"lot-a") #= available.\n')

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert [term.text for term in statement.n_atoms[0].application.arguments] == [
        "product(7)",
        '"lot-a"',
    ]
    assert statement.n_atoms[0].value.text == "available"


def test_accepts_zero_arity_non_herbrand_function() -> None:
    program = parse_program("#nherb mode/0.\nmode #= active.\n")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].application.render() == "mode"
