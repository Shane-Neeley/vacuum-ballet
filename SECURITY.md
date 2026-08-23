# Security

This project can control a physical device and stores an authenticated session
cache locally. Treat it like home-automation infrastructure.

## Do not disclose

- Roborock email addresses or passwords;
- verification codes;
- session-cache files under `~/.cache/vacuum-ballet/`;
- `.env` files, logs, or map images that reveal private spaces.

The repository ignores `.env`, `.env.ballet`, virtual environments, and logs.
Verify `git status` before committing.

## Reporting a vulnerability

Do not publish working credentials, tokens, or an exploit in a public issue.
Use GitHub’s private vulnerability-reporting path for the repository if it is
enabled; otherwise contact the maintainer privately before disclosure.

When reporting, include the affected command or file, reproduction steps with
secrets removed, and the smallest safe demonstration. Physical-device issues
should state whether a real command can be sent without the confirmation gate.
