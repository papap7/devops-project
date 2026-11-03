  # Incident log

Every failure I hit, newest first. One entry per incident. The goal is to show how I diagnose problems, so I write down what I tried and what was wrong, not just the fix.

| # | Date | Phase | Title | Time lost |
|---|------|-------|-------|-----------|
| 3 | 2026-11-04 | 1 | Experiment: invalid cloud-init.yaml still booted, status said done | 35 min |
| 2 | 2026-11-03 | 1 | Experiment: empty GATEWAY_IP stopped first boot, VM left without a firewall | 5 min |
| 1 | 2026-10-28 | 1 | runcmd script aborted, Docker never installed | 30 min |

---

## #3: Experiment: invalid cloud-init.yaml still booted, status said done
**Date:** 2026-11-04 | **Phase:** 1 | **Component:** cloud-init (schema, user-data) | **Time lost:** 35 min

**This was a deliberate experiment on a throwaway VM (`devboxtest`), not a surprise failure.** First run: I changed the header `#cloud-config` to `# cloud-config` (with a space) and `package_update: true` to `package-update:` with `- true` underneath (hyphenated key, list instead of boolean). Second run: only the header change, to separate the two.

**My predictions:** the schema check would catch it, the launch would not fail, and `cloud-init status` would report a syntax error. The first two were right. The third was wrong.

**Symptom:** `multipass launch` printed `Launched: devboxtest`, and `cloud-init status --wait --long` returned `status: done` with `extended_status: degraded done`, `errors: []`, and a single `recoverable_errors` warning: `cloud-config failed schema validation!`. The runcmd script ran to the end: Docker and UFW were set up, and I could SSH in as `ubuntu` with my key and `id` showed the `docker` group.

**Diagnosis:** The warning told me to run `sudo cloud-init schema --system` inside the VM. That reported `package_update: [True] is not of type 'boolean'`. The key name in the message did not match what I typed (`package-update`), which showed that cloud-init treats the hyphenated key as `package_update`. The value `- true` made it a list, `[True]`, where a boolean is expected. `/var/log/cloud-init-output.log` had the same warning and showed the script finishing. For the header, I noticed on the first VM that `# cloud-config` had become `#cloud-config`. On the second run (header change only) I read `/var/lib/cloud/instance/user-data.txt` on the VM: it starts with `#cloud-config`, no space, so Multipass rewrote the file before cloud-init saw it. This run therefore never tested what cloud-init does with a wrong header. Multipass hides that mistake.

**Root cause:** Two separate things. (1) Schema validation in cloud-init is advisory: a wrong type is logged as a warning and the boot continues, so an invalid file produced a VM that looked healthy (`status: done`, `errors: []`). The only signal was `degraded done` and one line under `recoverable_errors`. A wrong type is also not a YAML syntax error, because the file was valid YAML. (2) Multipass parses and rewrites my YAML, so a bad header never reaches cloud-init.

**Fix:** Nothing to fix in the project. Cleanup after the experiment: restore `cloud-init.yaml` (`#cloud-config`, `package_update: true`), check that `git diff` is empty, and delete `devboxtest`. Nothing from the experiment is committed.

**Prevention:** `status: done` does not mean healthy. After every launch check `extended_status` and `recoverable_errors`, not only `status`. Validate the file before launching: running `cloud-init schema --config-file ... --annotate` in the existing `lab` VM rejected the broken file with `Invalid schema: user-data` and needed no new VM. Running the check on the Mac does not work: Homebrew has no `cloud-init` formula, and `pip install cloud-init` in a virtual environment (Python 3.15.2) fails with `ERROR: No matching distribution found for cloud-init (from versions: none)`. I did not find out whether the cause is the package, the platform or the new Python version. A later improvement is to run the same schema check in GitHub Actions on a Linux runner, so every push validates the file.

**Evidence:** [`docs/evidence/incident-3.txt`](evidence/incident-3.txt) (status output, schema error, SSH check, the `lab` check, the header check and the pip result).

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
