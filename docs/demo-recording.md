# Recording the terminal demo

The repository includes equivalent deterministic demos for POSIX shells and
PowerShell. Install the project first with `python -m pip install -e ".[dev]"`.

## Run the demo

On macOS or Linux:

```console
sh scripts/demo.sh
```

On Windows PowerShell:

```console
powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
```

The script displays a source program, its reference translation, the normalized
model, and an unsatisfiable functionality conflict. It does not modify files.

## Record with VHS

[VHS](https://github.com/charmbracelet/vhs) can record the POSIX demo with a
small tape file outside the repository:

```text
Output aspf-next-demo.gif
Set Width 1000
Set Height 620
Set TypingSpeed 40ms
Type "sh scripts/demo.sh"
Enter
Sleep 5s
```

Run `vhs demo.tape` from an installed checkout. Review the generated GIF before
publishing it; generated media is intentionally not tracked in this repository.

## Record with asciinema

For a shareable terminal session without generating a binary asset in the
repository:

```console
asciinema rec -c "sh scripts/demo.sh" aspf-next-demo.cast
```

The `.cast` file can be played locally with `asciinema play`. Do not publish a
recording until its terminal contents have been checked for unrelated paths or
environment details.
