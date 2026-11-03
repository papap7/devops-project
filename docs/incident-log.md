  # Incident log

Every failure I hit, newest first. One entry per incident. The goal is to show how I diagnose problems, so I write down what I tried and what was wrong, not just the fix.

| # | Date | Phase | Title | Time lost |
|---|------|-------|-------|-----------|
| 2 | 2026-11-03 | 1 | Experiment: empty GATEWAY_IP stopped first boot, VM left without a firewall | 5 min |
| 1 | 2026-10-28 | 1 | runcmd script aborted, Docker never installed | 30 min |

---

## #2: Experiment: empty GATEWAY_IP stopped first boot, VM left without a firewall
**Date:** 2026-11-03 | **Phase:** 1 | **Component:** cloud-init (runcmd) | **Time lost:** 5 min

**This was a deliberate experiment on a throwaway VM (`devboxtest`), not a surprise failure.** I misspelled the variable on purpose (`GATEWY_IP=...` assigned, `GATEWAY_IP` read) to check that my guard and `set -eu` stop the script when something is wrong.

**Symptom:** `multipass launch` printed `Launched: devboxtest`, but `cloud-init status --wait --long` returned `status: error` with `scripts_user ... Runparts: 1 failures (runcmd)`. The VM booted and accepted connections as if nothing was wrong.

**Diagnosis:** Read the end of `/var/log/cloud-init-output.log`. It showed `FINISHED SETTING UP DOCKER.`, then `runcmd: 35: GATEWAY_IP: GATEWAY_IP is empty`, then the `scripts_user` warnings. `UFW setup starting...` never appeared, so the script stopped before the UFW block. Checked the VM: `docker --version` works, `ufw status verbose` says `Status: inactive`, and `ss -tlnp` shows sshd on port 22 with nothing filtering it. `dpkg -l ufw` shows the package installed (`ii`), but that comes from the base image, since my UFW install line never ran.

**Root cause:** the variable was assigned under one name and read under another. In POSIX sh an unset variable expands to an empty string, so without a check the next line would have run `ufw allow ... from  to any port 22` with the source missing. The message in the log is the text from my `${GATEWAY_IP:?...}` guard, so the guard is what stopped the script. (With `set -u` alone it would also have stopped, with a generic "parameter not set" message.)

**Fix:** No change to the guard. The script behaved as intended, and failing before `ufw --force enable` is the safe order. I reverted the deliberate typo in `cloud-init.yaml` (`GATEWY_IP` back to `GATEWAY_IP`) so it is never committed, and deleted `devboxtest`.

**Prevention:** `Launched:` only means the VM started, not that it is configured. Always run `cloud-init status --wait --long` after a launch and treat anything other than `status: done` as a broken VM. A failed first boot can leave a half-configured server (Docker installed, no firewall), and cloud-init does not run again, so delete and relaunch from the file instead of patching by hand. Keep the guard before any step that depends on a computed value.

**Evidence:** [`docs/evidence/incident-2.txt`](evidence/incident-2.txt) (status output, log tail, and the checks on the VM).

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
