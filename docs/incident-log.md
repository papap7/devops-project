# Incident log

Every failure I hit, newest first. One entry per incident. The goal is to show how I diagnose problems, so I write down what I tried and what was wrong, not just the fix.

| # | Date | Phase | Title | Time lost |
|---|------|-------|-------|-----------|
| 1 | 2026-10-28 | 1 | runcmd script aborted, Docker never installed | 30 min |

---

## #1: runcmd script aborted, Docker never installed
**Date:** 2026-10-28 | **Phase:** 1 | **Component:** cloud-init (runcmd) | **Time lost:** 30 min

**Symptom:** `cloud-init status` reported an error and the `scripts_user` module failed. Docker was not installed on the new VM.

**Diagnosis:** Ran `cloud-init status --format json`, then read `/var/log/cloud-init-output.log`. The log showed `runcmd: 2: set: Illegal option -o pipefail` followed by "Failed to run module scripts_user". `cloud-init schema --system` had passed, so the YAML was valid and the problem was inside the script.

**Root cause:** cloud-init runs `runcmd` scripts with `/bin/sh`, which is `dash` on Ubuntu. `dash` does not support `set -o pipefail`, so the script aborted on its first line.

**Fix:** Changed `set -euo pipefail` to `set -eu` (the script has no pipes, so nothing is lost for now). Deleted and relaunched the VM; first boot finished with `status: done` and no errors, and `docker version` and `docker compose version` work.

**Prevention:** `runcmd` is POSIX sh, not bash, so bash-only features need an explicit bash. Schema validation only checks the YAML, so always read `cloud-init-output.log` after a first boot. Follow-up idea: run a shell linter on the script before launching.

**Evidence:** [`docs/evidence/incident-1.txt`](evidence/incident-1.txt) (log lines saved from the failed boot).

---

## Template

Copy this block for each new incident and add a row to the table at the top.

### #N: Title
**Date:** YYYY-MM-DD | **Phase:** N | **Component:** ... | **Time lost:** ...

**Symptom:** what I saw

**Diagnosis:** which logs and commands, in order, including wrong guesses

**Root cause:** the actual reason

**Fix:** what I changed

**Prevention:** what stops it from happening again

**Evidence:** link to saved output
