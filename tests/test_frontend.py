from __future__ import annotations

import pytest

from aspf_next.errors import UnsupportedSyntaxError
from aspf_next.frontend import parse_program
from aspf_next.ir import (
    ApplicationOperand,
    AspfStatement,
    Assignment,
    BodyComparison,
    GroundTermKind,
    NAtomOperator,
    OrdinaryStatement,
    ScalarOperand,
    VariableTerm,
)


def test_parses_declaration_and_basic_assignment() -> None:
    program = parse_program("#nherb balance/1.\nbalance(account1) #= 500.\n", filename="basic.aspf")

    assert [(item.name, item.arity) for item in program.declarations] == [("balance", 1)]
    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assignment = statement.n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert assignment.target.render() == "balance(account1)"
    assert assignment.value.text == "500"


def test_parses_historical_application_style_declarations() -> None:
    program = parse_program(
        "#nherb f(X).\n#nherb pair(Left,Right).\nf(a) #= one.\npair(a,b) #= two.\n"
    )

    assert [(item.name, item.arity) for item in program.declarations] == [
        ("f", 1),
        ("pair", 2),
    ]


def test_equivalent_declarations_are_harmless_and_deduplicated() -> None:
    program = parse_program("#nherb f/1.\n#nherb f(X).\n#nherb f/1.\nf(a) #= value.\n")

    assert [(item.name, item.arity) for item in program.declarations] == [("f", 1)]


@pytest.mark.parametrize(
    "declaration",
    ["#nherb f().", "#nherb f(1).", "#nherb f(X+1).", "#nherb f(g(X))."],
)
def test_application_style_declarations_require_placeholders(declaration: str) -> None:
    with pytest.raises(UnsupportedSyntaxError, match="placeholder-only") as caught:
        parse_program(declaration, filename="declaration.aspf")

    assert caught.value.location.filename == "declaration.aspf"
    assert caught.value.location.line == 1
    assert caught.value.location.column == 1


def test_same_name_declarations_at_multiple_arities_are_distinct() -> None:
    program = parse_program(
        "#nherb f/0.\n#nherb f(X).\n#nherb f/2.\nf #= zero.\nf(a) #= one.\nf(a,b) #= two.\n"
    )

    assert {(item.name, item.arity) for item in program.declarations} == {
        ("f", 0),
        ("f", 1),
        ("f", 2),
    }
    assignments = [
        n_atom
        for statement in program.statements
        if isinstance(statement, AspfStatement)
        for n_atom in statement.n_atoms
    ]
    assert [item.target.render() for item in assignments if isinstance(item, Assignment)] == [
        "f",
        "f(a)",
        "f(a,b)",
    ]


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
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert comparison.span.start < comparison.span.end


def test_parses_positive_ground_not_equal_body_literal() -> None:
    program = parse_program(
        "#nherb balance/1.\ndifferent :- balance(account1) #!= 500.\n",
        filename="not-equal.aspf",
    )

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert comparison.left.render() == "balance(account1)"
    assert isinstance(comparison.right, ScalarOperand)
    assert comparison.right.text == "500"
    assert comparison.operator is NAtomOperator.NOT_EQUAL


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
    assignment = statement.n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert assignment.target.application.arguments[0].text == "account1"


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
    "source",
    [
        "#nherb balance/1.\nbalance(account1).\n",
        "#nherb balance/1.\np(balance(account1)).\n",
    ],
)
def test_preserves_declared_non_herbrand_symbol_outside_n_atom(source: str) -> None:
    program = parse_program(source)

    assert len(program.declarations) == 1
    assert isinstance(program.statements[0], OrdinaryStatement)


def test_preserves_declared_symbol_outside_n_atom_in_mixed_rule() -> None:
    source = "#nherb balance/1.\np(balance(a)) :- balance(a) #= 1.\n"

    program = parse_program(source, filename="mixed.aspf")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert len(statement.n_atoms) == 1


def test_declared_symbol_text_in_comments_and_strings_is_inert() -> None:
    program = parse_program('#nherb balance/1.\nlabel("balance"). % balance(a).\n')

    assert len(program.declarations) == 1


def test_rejects_declared_zero_arity_symbol_as_n_atom_value() -> None:
    source = "#nherb mode/0.\n#nherb status/1.\nstatus(alice) #= mode.\n"

    with pytest.raises(UnsupportedSyntaxError, match="only as a complete positive") as caught:
        parse_program(source, filename="value.aspf")

    assert caught.value.location.line == 3
    assert caught.value.location.column == 18


def test_rejects_declared_zero_arity_symbol_as_n_atom_argument() -> None:
    source = "#nherb current/0.\n#nherb reading/1.\nreading(current) #= active.\n"

    with pytest.raises(UnsupportedSyntaxError, match="nested declared") as caught:
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
    assert isinstance(comparison, BodyComparison)
    assert comparison.operator is operator
    assert isinstance(comparison.right, ScalarOperand)
    assert comparison.right.kind is GroundTermKind.INTEGER


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
    atoms = [atom for statement in asp_statements for atom in statement.n_atoms]
    assert isinstance(atoms[0], Assignment)
    assert isinstance(atoms[1], BodyComparison)
    assert atoms[1].operator is operator


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
    atoms = [atom for statement in asp_statements for atom in statement.n_atoms]
    assert isinstance(atoms[0], Assignment)
    assert isinstance(atoms[1], BodyComparison)
    assert atoms[1].operator is NAtomOperator.NOT_EQUAL


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
            "only as a complete positive rule-body literal",
        ),
        (
            "#nherb first/1.\nfirst(a) #= ordinary(Value).\n",
            "variables as n-atom values",
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

    with pytest.raises(UnsupportedSyntaxError, match=r"pair/1.*declared arities: 2"):
        parse_program("#nherb pair/2.\npair(a) #= yes.")


def test_accepts_integer_symbol_string_and_ordinary_ground_function_terms() -> None:
    program = parse_program('#nherb item/2.\nitem(product(7),"lot-a") #= available.\n')

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assignment = statement.n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert [term.text for term in assignment.target.application.arguments] == [
        "product(7)",
        '"lot-a"',
    ]
    assert assignment.value.text == "available"


def test_accepts_nested_ground_herbrand_assignment_value() -> None:
    program = parse_program("#nherb f/1.\nf(a) #= wrapper(k(1),inner(value)).\n")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assignment = statement.n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert assignment.value.kind is GroundTermKind.FUNCTION
    assert assignment.value.text == "wrapper(k(1),inner(value))"


def test_rejects_declared_application_nested_in_herbrand_value() -> None:
    source = "#nherb f/1.\n#nherb k/1.\nf(a) #= wrapper(k(1)).\n"

    with pytest.raises(UnsupportedSyntaxError, match="declared non-Herbrand application") as caught:
        parse_program(source, filename="nested-value.aspf")

    assert caught.value.location.line == 3
    assert caught.value.location.column == source.splitlines()[2].index("k(1)") + 1


def test_undeclared_right_function_is_scalar_but_declared_right_function_is_application() -> None:
    undeclared = parse_program("#nherb f/1.\nsame :- f(a) #= k(1).\n")
    declared = parse_program("#nherb f/1.\n#nherb k/1.\nsame :- f(a) #= k(1).\n")

    undeclared_statement = undeclared.statements[0]
    declared_statement = declared.statements[0]
    assert isinstance(undeclared_statement, AspfStatement)
    assert isinstance(declared_statement, AspfStatement)
    undeclared_comparison = undeclared_statement.n_atoms[0]
    declared_comparison = declared_statement.n_atoms[0]
    assert isinstance(undeclared_comparison, BodyComparison)
    assert isinstance(declared_comparison, BodyComparison)
    assert isinstance(undeclared_comparison.right, ScalarOperand)
    assert undeclared_comparison.right.kind is GroundTermKind.FUNCTION
    assert isinstance(declared_comparison.right, ApplicationOperand)


def test_undeclared_arity_of_declared_name_remains_a_herbrand_value() -> None:
    program = parse_program("#nherb f/1.\n#nherb k/2.\nsame :- f(a) #= k(1).\n")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert isinstance(comparison.right, ScalarOperand)
    assert comparison.right.text == "k(1)"


def test_accepts_zero_arity_non_herbrand_function() -> None:
    program = parse_program("#nherb mode/0.\nmode #= active.\n")

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assignment = statement.n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert assignment.target.render() == "mode"


def test_parses_domain_safe_variable_as_typed_direct_application_argument() -> None:
    source = "#nherb balance/1.\nlow(A) :- account(A), balance(A) #< 1000.\n"

    program = parse_program(source, filename="variables.aspf")
    statement = program.statements[0]

    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    argument = comparison.left.application.arguments[0]
    assert isinstance(argument, VariableTerm)
    assert argument.name == argument.text == "A"
    assert comparison.left.render() == "balance(A)"
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
    comparison_node = statement.n_atoms[0]
    assert isinstance(comparison_node, BodyComparison)
    assert comparison_node.left.render() == "balance(A)"


def test_accepts_domain_safe_variable_in_assignment_head() -> None:
    program = parse_program(
        "#nherb status/1.\nperson(alice;bob).\nstatus(P) #= active :- person(P).\n"
    )

    statement = program.statements[1]
    assert isinstance(statement, AspfStatement)
    assignment = statement.n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert assignment.target.render() == "status(P)"


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
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert comparison.left.render() == "balance(A)"


def test_parses_typed_application_operands_with_precise_spans() -> None:
    source = """#nherb actual/1.
#nherb expected/1.
account(a).
same(A) :- account(A), actual(A) #= expected(A).
"""

    program = parse_program(source, filename="operands.aspf")
    statement = program.statements[1]

    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert isinstance(comparison.left, ApplicationOperand)
    assert isinstance(comparison.right, ApplicationOperand)
    assert comparison.left.render() == "actual(A)"
    assert comparison.right.render() == "expected(A)"
    assert comparison.operator is NAtomOperator.EQUAL
    assert comparison.right.span.start == source.index("expected(A)")
    assert comparison.right.span.end == comparison.right.span.start + len("expected(A)")


def test_scalar_assignment_and_body_comparison_are_distinct_ir_nodes() -> None:
    program = parse_program("#nherb actual/1.\nactual(a) #= 10.\nsame :- actual(a) #= 10.\n")
    statements = [
        statement for statement in program.statements if isinstance(statement, AspfStatement)
    ]

    assignment = statements[0].n_atoms[0]
    comparison = statements[1].n_atoms[0]
    assert isinstance(assignment, Assignment)
    assert isinstance(assignment.value, ScalarOperand)
    assert isinstance(comparison, BodyComparison)
    assert isinstance(comparison.right, ScalarOperand)


@pytest.mark.parametrize("operator", ["#=", "#!=", "#<", "#<=", "#>", "#>="])
def test_accepts_declared_application_as_right_body_operand(operator: str) -> None:
    program = parse_program(
        f"#nherb actual/0.\n#nherb expected/0.\nokay :- actual {operator} expected.\n"
    )

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert isinstance(comparison.right, ApplicationOperand)
    assert comparison.right.render() == "expected"


def test_accepts_two_independently_safe_application_variables() -> None:
    program = parse_program(
        "#nherb actual/1.\n#nherb expected/1.\n"
        "pair(A,B) :- account(A), account(B), actual(A) #= expected(B).\n"
    )

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    comparison = statement.n_atoms[0]
    assert isinstance(comparison, BodyComparison)
    assert comparison.left.render() == "actual(A)"
    assert isinstance(comparison.right, ApplicationOperand)
    assert comparison.right.render() == "expected(B)"


@pytest.mark.parametrize(
    ("body", "token"),
    [
        ("account(B), actual(A) #= expected(B)", "A"),
        ("account(A), actual(A) #= expected(B)", "B"),
        ("actual(A) #= expected(B)", "A"),
    ],
)
def test_rejects_unsafe_variables_from_either_application(body: str, token: str) -> None:
    source = f"#nherb actual/1.\n#nherb expected/1.\nsame(A,B) :- {body}.\n"

    with pytest.raises(UnsupportedSyntaxError, match="ordinary positive body atom") as caught:
        parse_program(source, filename="unsafe-operands.aspf")

    assert caught.value.location.line == 3
    comparison_text = source.splitlines()[2].split(":-", maxsplit=1)[1]
    expected_column = (
        source.splitlines()[2].index(comparison_text) + comparison_text.index(token) + 1
    )
    assert caught.value.location.column == expected_column


@pytest.mark.parametrize(
    ("right", "message", "token"),
    [
        ("missing(A)", "variables as n-atom values", "A"),
        ("expected(A,B)", "variables as n-atom values", "A"),
        ("expected(_V)", "non-Herbrand variables", "_V"),
        ("expected(owner(A))", "complete direct arguments", "A"),
    ],
)
def test_rejects_invalid_right_application_at_offending_token(
    right: str, message: str, token: str
) -> None:
    source = (
        "#nherb actual/1.\n#nherb expected/1.\naccount(a).\n"
        f"same(A) :- account(A), actual(A) #= {right}.\n"
    )

    with pytest.raises(UnsupportedSyntaxError, match=message) as caught:
        parse_program(source, filename="right.aspf")

    line = source.splitlines()[3]
    assert caught.value.location.line == 4
    assert caught.value.location.column == line.index(token, line.index("#=")) + 1


@pytest.mark.parametrize(
    ("source_tail", "message"),
    [
        ("actual(a) #= expected(a).", "only as a complete positive rule-body literal"),
        ("same :- not actual(a) #= expected(a).", "default-negated n-atoms"),
        (
            "same :- #count { X : actual(a) #= expected(a) } > 0.",
            "aggregates or choice",
        ),
        ("{ same : actual(a) #= expected(a) }.", "aggregates or choice"),
        ("same :- actual(a) #= expected(a) : guard.", "conditional literals"),
        ("same :- actual(a) #= expected(a) + 1.", "arithmetic"),
    ],
)
def test_rejects_unsupported_application_comparison_placements_and_arithmetic(
    source_tail: str, message: str
) -> None:
    source = "#nherb actual/1.\n#nherb expected/1.\n" + source_tail + "\n"

    with pytest.raises(UnsupportedSyntaxError, match=message) as caught:
        parse_program(source, filename="placement.aspf")

    assert caught.value.location.filename == "placement.aspf"
    assert caught.value.location.line == 3
    assert caught.value.location.column >= 1


def test_multiple_application_comparisons_can_share_safe_source_variables() -> None:
    program = parse_program(
        "#nherb actual/1.\n#nherb expected/1.\n#nherb baseline/1.\n"
        "okay(A) :- account(A), actual(A) #= expected(A), actual(A) #!= baseline(A).\n"
    )

    statement = program.statements[0]
    assert isinstance(statement, AspfStatement)
    assert len(statement.n_atoms) == 2
    assert all(isinstance(atom, BodyComparison) for atom in statement.n_atoms)
