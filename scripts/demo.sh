#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
cd "$PROJECT_ROOT"

printf '\n== ASP{f} source ==\n'
sed -n '1,120p' examples/01_basic_assignment.aspf

printf '\n== Reference lowering ==\n'
aspf examples/01_basic_assignment.aspf --emit-lowered

printf '\n== Normalized model ==\n'
aspf examples/01_basic_assignment.aspf

printf '\n== Functionality conflict ==\n'
aspf examples/04_conflicting_values.aspf
