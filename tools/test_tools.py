#!/usr/bin/env python3
# tools/test_tools.py
#
# Runs every module's --selftest and totals the checks. The total is PRINTED
# and is not stored anywhere in the repository: a check count written into a
# document is a second place for it to drift, and this directory's whole
# subject is a number whose provenance nobody can see.
#
# Standard library only. Parses under Python 3.9.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = ["typed.py", "channel_loss.py", "rerun_find_rate.py",
           "residual_partition.py", "two_body_source.py"]


def main() -> int:
    total, failed = 0, 0
    for mod in MODULES:
        p = subprocess.run([sys.executable, os.path.join(HERE, mod), "--selftest"],
                           capture_output=True, text=True, cwd=HERE)
        out = (p.stdout + p.stderr).strip()
        m = re.search(r"(\d+) checks, (\d+) failed", out)
        if p.returncode != 0 or not m:
            print("%-24s FAILED" % mod)
            print(out)
            failed += 1
            continue
        total += int(m.group(1))
        print("%-24s %s" % (mod, out.splitlines()[-1]))

    # Every module must run its fixture when handed nothing.
    for mod in MODULES[1:]:
        p = subprocess.run([sys.executable, os.path.join(HERE, mod)],
                           capture_output=True, text=True, cwd=HERE)
        if p.returncode != 0:
            print("%-24s fixture run FAILED" % mod)
            print((p.stdout + p.stderr)[-2000:])
            failed += 1

    # THE SHARED RULE, screened: the word is never a return VALUE.
    #
    # It is allowed to appear where a tool NAMES what it refuses to return --
    # a module cannot state its own subject otherwise. That exemption is
    # DECLARED line by line below and measured in three arms, because an
    # exemption nobody counts is a hole nobody can see:
    #   arm 1  with the exemption applied, no fixture output fires
    #   arm 2  without it, the ONLY lines that fire are the declared ones
    #   arm 3  a planted violation is caught through the exemption
    exempt = (
        "N3 residual_partition.py -- the residual is not noise",
        "the residual is not noise",
    )

    def hits(text):
        return [ln for ln in text.splitlines()
                if "noise" in ln.lower()
                and "noise-as-information" not in ln.lower()]

    for mod in MODULES[1:]:
        p = subprocess.run([sys.executable, os.path.join(HERE, mod)],
                           capture_output=True, text=True, cwd=HERE)
        raw = hits(p.stdout)
        live = [ln for ln in raw if ln.strip() not in exempt]
        if live:
            print("%-24s output carries the refused word as a value" % mod)
            for ln in live:
                print("    " + ln)
            failed += 1
        if mod == "residual_partition.py":
            if not raw:
                print("%-24s ARM 2 FAILED: the declared exemption never fires, "
                      "so it is forgiving nothing and should be deleted" % mod)
                failed += 1
            planted = p.stdout + "\n  verdict: noise\n"
            if not [ln for ln in hits(planted) if ln.strip() not in exempt]:
                print("%-24s ARM 3 FAILED: a planted violation is not caught" % mod)
                failed += 1

    print()
    print("tools/: %d checks across %d modules, %d module failures"
          % (total, len(MODULES), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
