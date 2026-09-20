"""Release smoke: is the deployed service healthy, and is it *this* release?

Phase 5, §22 / AC10. `status=ok` on its own proves nothing about a deploy: a
perfectly healthy previous version answers exactly the same. So the check is
both — `status` is `ok`, and `version` is the SHA that was just pushed.

Usage:
    python scripts/check_release.py https://<domain>/health <expected-sha>

Exit code 0 only when both hold. Everything it prints goes to stderr and
contains no secrets: the URL, the reported status and the two SHAs.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

ATTEMPTS = 12
DELAY_S = 5
TIMEOUT_S = 10


def probe(url: str, expected_sha: str) -> tuple[bool, str]:
    """(ok, explanation) for one attempt."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response:  # noqa: S310
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, f"unreachable: {exc}"

    status = payload.get("status")
    version = payload.get("version")
    if status != "ok":
        return False, f"status={status} checks={payload.get('checks')}"
    if expected_sha and version != expected_sha:
        return False, f"version={version} expected={expected_sha}"
    return True, f"status=ok version={version}"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_release.py <health-url> [expected-sha]", file=sys.stderr)
        return 2
    url, expected_sha = argv[0], (argv[1] if len(argv) > 1 else "")

    last = "no attempt made"
    for attempt in range(1, ATTEMPTS + 1):
        ok, last = probe(url, expected_sha)
        if ok:
            print(f"release smoke passed: {last}", file=sys.stderr)
            return 0
        print(f"attempt {attempt}/{ATTEMPTS}: {last}", file=sys.stderr)
        if attempt < ATTEMPTS:
            time.sleep(DELAY_S)
    print(f"release smoke failed: {last}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
