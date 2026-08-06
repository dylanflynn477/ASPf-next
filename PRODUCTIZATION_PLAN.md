# Milestone 0.1 productization plan

## Goal

Present the existing milestone 0.1 implementation as careful, usable research
software without expanding its ASP{f} semantics. The parser, IR, lowering, and
solver remain unchanged unless a narrowly scoped usability defect is discovered.

## Work

1. Turn `README.md` into an accessible landing page with accurate badges, a
   two-minute trial path, an inspectable lowering example, architecture summary,
   limitations, provenance, and links to deeper documentation.
2. Replace the unnumbered examples with a five-step progression covering an
   assignment, partiality, a conditional assignment, conflicting values, and
   ordinary ASP model enumeration. Document and automatically execute every
   example.
3. Add a tutorial, Mermaid architecture diagram, deterministic POSIX and
   PowerShell demo scripts, recording instructions, and portfolio-ready copy.
4. Add alpha release notes, a changelog, a restrained roadmap, contribution
   guidance, issue forms, a pull-request template, and accurate package metadata.
5. Add regression tests for documented examples, demo inputs, README command
   assumptions, release metadata, and documentation links where practical.

## Commit sequence

1. Record this productization plan.
2. Add guided examples, demos, and their regression tests.
3. Restructure user-facing and architectural documentation.
4. Add release, contribution, portfolio, and repository metadata.
5. Apply final review corrections found by the complete quality and smoke-test
   pass.

## Validation

Run:

```console
ruff format --check src tests
ruff check src tests
mypy src
pytest
```

Then create a fresh virtual environment, install with
`python -m pip install -e ".[dev]"`, run the basic example through the installed
`aspf` entry point, exercise lowering and JSON output, and inspect the full diff.

## Boundaries and release decisions

- Keep version `0.1.0`; the release name `0.1.0-alpha` describes project status
  without introducing a conflicting package version during this documentation
  milestone.
- Describe the backend only as a correctness-oriented reference translation.
- Keep unsupported syntax explicit and link to the normative language boundary.
- Treat native backends and expanded operators as proposed research, not shipped
  or promised functionality.
- Prepare release text but do not create a tag, GitHub Release, or merge.

