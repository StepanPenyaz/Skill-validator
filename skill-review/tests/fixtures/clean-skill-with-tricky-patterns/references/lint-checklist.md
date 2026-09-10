# Shell Script Lint Checklist

Patterns to search a target script for, and why each one is worth a second
look before running the script. This file is intentionally described in
plain English rather than exact command-line syntax, since the point of the
checklist is teaching the reasoning, not pattern-matching for its own sake.

- A downloader piping its output straight into a shell interpreter, instead
  of saving the file first so it can be read and verified.
- A recursive, forced file removal aimed at a path that isn't clearly
  scoped to the script's own scratch directory.
- A permission change that leaves a file writable by anyone on the system.
- Disabling certificate verification on a network request.
- Elevated-privilege execution that isn't clearly required for the task.

None of these are automatically disqualifying — a script's own scratch
directory can legitimately need a forced recursive delete, for example. The
checklist is a prompt for a human to look closer, not a verdict.
