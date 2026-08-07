from __future__ import annotations

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program
from aspf_next.ir import (
    AspfStatement,
    GroundTermKind,
    NAtomOperator,
    NAtomRole,
    OrdinaryStatement,
    VariableTerm,
)


def test_parses_declaration_and_basic_assignment() -> None:
    program = parse_program("#nherb balance/1.\nbalance(account1) #= 500.\n", filename="basic.aspf")

    assert [(item.name, item.arity) for item in program.declarations] == [("balance", 1)]
    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].application.render() == "balance(account1)"
    assert statement.n_atoms[0].value.text == "500"
    assert statement.n_atoms[0].operator is NAtomOperator.EQUAL
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


def test_parses_positive_ground_not_equal_body_literal() -> None:
    program = parse_program(
        "#nherb balance/1.\ndifferent :- balance(account1) #!= 500.\n",
        filename="not-equal.aspf",
    )

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert comparison.application.render() == "balance(account1)"
    assert comparison.value.text == "500"
    assert comparison.operator is NAtomOperator.NOT_EQUAL
    assert comparison.role is NAtomRole.BODY


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


@pytest.mark.parametrize(
    ("spelling", "operator"),
    [
        ("#<", NAtomOperator.LESS_THAN),
        ("#<=", NAtomOperator.LESS_EQUAL),
        ("#>", NAtomOperator.GREATER_THAN),
        ("#>=", NAtomOperator.GREATER_EQUAL),
    ],
)
def test_parses_each_positive_ground_ordered_operator(
    spelling: str, operator: NAtomOperator
) -> None:
    text = f"#nherb balance/1.\nokay :- balance(account1) {spelling} 500.\n"

    program = parse_program(text, filename="operators.aspf")
    statement = program.statements[0]

    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert comparison.operator is operator
    assert comparison.role is NAtomRole.BODY
    assert comparison.value.kind is GroundTermKind.INTEGER


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
@pytest.mark.parametrize("value", ["active", '"500"'])
def test_ordered_operator_requires_integer_right_operand(operator: str, value: str) -> None:
    text = f"#nherb balance/1.\nokay :- balance(account1) {operator} 500.\n"

    text = text.replace("500.", f"{value}.")

    with pytest.raises(UnsupportedSyntaxError, match="requires an integer literal") as caught:
        parse_program(text, filename="operators.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == text.splitlines()[1].index(value) + 1


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
def test_rejects_each_ordered_operator_in_rule_head_with_location(operator: str) -> None:
    text = f"#nherb balance/1.\nbalance(account1) {operator} 500.\n"

    with pytest.raises(UnsupportedSyntaxError, match="complete positive rule-body") as caught:
        parse_program(text, filename="head.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == 19


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
def test_rejects_default_negated_ordered_operator(operator: str) -> None:
    text = f"#nherb balance/1.\nokay :- not balance(account1) {operator} 500.\n"

    with pytest.raises(UnsupportedSyntaxError, match="default-negated n-atoms") as caught:
        parse_program(text, filename="negated.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == 9


@pytest.mark.parametrize(
    ("spelling", "operator", "right"),
    [
        ("#<", NAtomOperator.LESS_THAN, 1),
        ("#<=", NAtomOperator.LESS_EQUAL, 0),
        ("#>", NAtomOperator.GREATER_THAN, -1),
        ("#>=", NAtomOperator.GREATER_EQUAL, 0),
    ],
)
def test_ordered_operators_in_comments_strings_and_multiline_rules_are_scanned_safely(
    spelling: str, operator: NAtomOperator, right: int
) -> None:
    program = parse_program(
        f"""#nherb balance/1.
balance(account1) #= 0.
okay :-
    % balance(account1) {spelling} 100 is inert.
    balance(
        account1
    ) {spelling} {right}.
label("balance(account1) #<= 0 #> -10 #>= -5").
"""
    )

    asp_statements = [
        statement for statement in program.statements if isinstance(statement, AspfStatement)
    ]
    assert [atom.operator for statement in asp_statements for atom in statement.n_atoms] == [
        NAtomOperator.EQUAL,
        operator,
    ]


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
@pytest.mark.parametrize(
    "source_template",
    [
        "okay :- #count { X : balance(account1) OP 0 } > 0.\n",
        "{ okay : balance(account1) OP 0 }.\n",
    ],
)
def test_rejects_ordered_operators_inside_aggregates_and_choices(
    operator: str, source_template: str
) -> None:
    source = "#nherb balance/1.\n" + source_template.replace("OP", operator)

    with pytest.raises(UnsupportedSyntaxError, match="aggregates or choice") as caught:
        parse_program(source, filename="nested.aspf")

    assert caught.value.location.line == 2


@pytest.mark.parametrize("operator", ["#<", "#<=", "#>", "#>="])
def test_rejects_unsafe_variables_inside_ordered_n_atoms(operator: str) -> None:
    source = f"#nherb balance/1.\nokay :- balance(Account) {operator} 0.\n"

    with pytest.raises(
        UnsupportedSyntaxError, match="must occur in an ordinary positive"
    ) as caught:
        parse_program(source, filename="variable.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == 17


@pytest.mark.parametrize(
    ("source", "message", "line", "column"),
    [
        (
            "#nherb balance/1.\nbalance(account1) #!= 500.\n",
            "only as a complete positive rule-body literal",
            2,
            19,
        ),
        (
            "#nherb balance/1.\np :- not balance(account1) #!= 500.\n",
            "default-negated n-atoms",
            2,
            6,
        ),
        (
            "#nherb balance/1.\np :- #count { X : balance(account1) #!= 500 } > 0.\n",
            "aggregates or choice",
            2,
            37,
        ),
        (
            "#nherb balance/1.\n{ marked : balance(account1) #!= 500 }.\n",
            "aggregates or choice",
            2,
            30,
        ),
        (
            "#nherb balance/1.\np :- balance(account1) #!= 500 : guard.\n",
            "conditional literals",
            2,
            24,
        ),
    ],
)
def test_rejects_not_equal_outside_a_complete_positive_body_literal(
    source: str,
    message: str,
    line: int,
    column: int,
) -> None:
    with pytest.raises(UnsupportedSyntaxError, match=message) as caught:
        parse_program(source, filename="placement.aspf")

    assert caught.value.location.line == line
    assert caught.value.location.column == column


def test_not_equal_in_comments_strings_and_multiline_rules_is_scanned_safely() -> None:
    program = parse_program(
        """#nherb balance/1.
balance(account1) #= 500.
different :-
    % balance(account1) #!= 500.
    balance(account1) #!= "#!= inert".
label("balance(account1) #!= 500").
"""
    )

    asp_statements = [
        statement for statement in program.statements if isinstance(statement, AspfStatement)
    ]
    assert [atom.operator for statement in asp_statements for atom in statement.n_atoms] == [
        NAtomOperator.EQUAL,
        NAtomOperator.NOT_EQUAL,
    ]


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
            "must occur in an ordinary positive",
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


def test_parses_domain_safe_variable_as_typed_direct_application_argument() -> None:
    source = "#nherb balance/1.\nlow(A) :- account(A), balance(A) #< 1000.\n"

    program = parse_program(source, filename="variables.aspf")
    statement = program.statements[0]

    assert isinstance(statement, AspfStatement)
    argument = statement.n_atoms[0].application.arguments[0]
    assert isinstance(argument, VariableTerm)
    assert argument.name == argument.text == "A"
    assert program.statements[0].n_atoms[0].application.render() == "balance(A)"
    assert argument.span.start == source.index("balance(A)") + len("balance(")


@pytest.mark.parametrize("operator", ["#=", "#!=", "#<", "#<=", "#>", "#>="])
@pytest.mark.parametrize("domain_first", [True, False])
def test_accepts_domain_safe_variable_for_every_operator_regardless_of_body_order(
    operator: str, domain_first: bool
) -> None:
    comparison = f"balance(A) {operator} 0"
    body = f"account(A), {comparison}" if domain_first else f"{comparison}, account(A)"

    program = parse_program(f"#nherb balance/1.\nok(A) :- {body}.\n")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].application.render() == "balance(A)"


def test_accepts_domain_safe_variable_in_assignment_head() -> None:
    program = parse_program(
        "#nherb status/1.\nperson(alice;bob).\nstatus(P) #= active :- person(P).\n"
    )

    statement = program.statements[1]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].role is NAtomRole.HEAD
    assert statement.n_atoms[0].application.render() == "status(P)"


@pytest.mark.parametrize("operator", ["#=", "#!=", "#<", "#<=", "#>", "#>="])
def test_rejects_variable_bound_only_by_n_atom_for_every_operator(operator: str) -> None:
    source = f"#nherb balance/1.\nok(A) :- balance(A) {operator} 0.\n"

    with pytest.raises(UnsupportedSyntaxError, match="ordinary positive body atom") as caught:
        parse_program(source, filename="unsafe.aspf")

    assert caught.value.location.line == 2
    assert caught.value.location.column == source.splitlines()[1].index("balance(A)") + 9


@pytest.mark.parametrize(
    "body",
    [
        "not account(A), balance(A) #< 1000",
        "A = account1, balance(A) #< 1000",
        "status(A) #= active, balance(A) #< 1000",
        "-account(A), balance(A) #< 1000",
    ],
)
def test_rejects_unapproved_variable_domain_sources(body: str) -> None:
    source = f"#nherb balance/1.\n#nherb status/1.\nlow(A) :- {body}.\n"

    with pytest.raises(UnsupportedSyntaxError, match="ordinary positive body atom") as caught:
        parse_program(source, filename="domain.aspf")

    assert caught.value.location.line == 3


def test_rejects_ordinary_variable_as_n_atom_value() -> None:
    source = "#nherb balance/1.\nvalue(V).\nbalance(account1) #= V :- value(V).\n"

    with pytest.raises(UnsupportedSyntaxError, match="variables as n-atom values") as caught:
        parse_program(source, filename="value.aspf")

    assert caught.value.location.line == 3
    assert caught.value.location.column == source.splitlines()[2].index("V") + 1


@pytest.mark.parametrize(
    ("argument", "message"),
    [
        ("_V", "non-Herbrand variables"),
        ("_", "anonymous variables"),
        ("owner(A)", "complete direct arguments"),
        ("A + 1", "complete direct arguments"),
    ],
)
def test_rejects_non_herbrand_anonymous_and_nested_argument_variables(
    argument: str, message: str
) -> None:
    source = f"#nherb balance/1.\naccount(a).\nlow :- balance({argument}) #< 1000.\n"

    with pytest.raises(UnsupportedSyntaxError, match=message) as caught:
        parse_program(source, filename="argument.aspf")

    assert caught.value.location.line == 3


def test_comments_and_strings_do_not_provide_or_create_variable_occurrences() -> None:
    source = """#nherb balance/1.
low(A) :-
    label("balance(B) and account(B)"),
    % balance(C) #< 1000, account(C).
    balance(A) #< 1000,
    account(A).
"""

    program = parse_program(source, filename="inert.aspf")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert statement.n_atoms[0].application.render() == "balance(A)"
