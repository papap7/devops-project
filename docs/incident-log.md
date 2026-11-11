  # Incident log

Every failure I hit, newest first. One entry per incident. The goal is to show how I diagnose problems, so I write down what I tried and what was wrong, not just the fix.

| # | Date | Phase | Title | Time lost |
|---|------|-------|-------|-----------|
| 6 | 2026-11-11 | 1 | Retyped EC2 firewall fix stopped first boot: CLOUD: parameter not set | 30 min |
| 5 | 2026-11-06 | 2 | flask --app app could not find the Flask application | 15 min |
| 4 | 2026-11-05 | 1 | Experiment: stopping docker.service did not stop Docker, the socket did | 30 min |
| 3 | 2026-11-04 | 1 | Experiment: invalid cloud-init.yaml still booted, status said done | 35 min |
| 2 | 2026-11-03 | 1 | Experiment: empty GATEWAY_IP stopped first boot, VM left without a firewall | 5 min |
| 1 | 2026-10-28 | 1 | runcmd script aborted, Docker never installed | 30 min |

---

## #6: Retyped EC2 firewall fix stopped first boot: CLOUD: parameter not set
**Date:** 2026-11-11 | **Phase:** 1 | **Component:** cloud-init (runcmd, POSIX sh), UFW | **Time lost:** 30 min

**Context:** before running `cloud-init.yaml` on AWS EC2 for the first time, I reviewed it for EC2 and found that my SSH rule would lock me out there. The rule allows SSH only from the VM's default gateway. On Multipass the gateway is my Mac, but in an AWS VPC it is the VPC router, and SSH from the internet keeps my home IP as the source. The rule would never match, so UFW's default deny would drop SSH. My `${GATEWAY_IP:?}` guard would not catch it, because the value is wrong, not empty. I did not launch the old file on EC2 to watch it fail; this part was found in review. The fix: read the platform with `cloud-init query v1.cloud_name`; on `aws`, allow 22/tcp in UFW and let the EC2 security group limit the source to my IP; everywhere else, keep the gateway rule. The failure below happened while I tested that fix locally.

**Symptom:** I typed the fix into `cloud-init.yaml` by hand and launched a throwaway VM (`devboxtest`). `/var/log/cloud-init-output.log` ended with `runcmd: 35: CLOUD: parameter not set`, then `Failed to run module scripts_user`. The last message from my script before it was `UFW setup starting...`, so the script stopped before `ufw --force enable`.

**Diagnosis:** the error names line 35 of the generated script, so I printed that part of it: `sudo sed -n '30,40p' /var/lib/cloud/instance/scripts/runcmd`. Line 35 was `$CLOUD=$(cloud-init query ...)`. I compared it with `git diff cloud-init.yaml`, which showed the same lines, so Multipass had not changed them: the mistake was in my file. Reviewing the diff line by line showed three more mistakes in the next two lines, and that `ssh_pwauth: false` was missing.

**Root cause:** four shell mistakes from retyping instead of copying:
1. `$CLOUD=...`: shell assigns with `CLOUD=...`. The `$` reads the variable instead, and with `set -u` reading an unset variable stops the script. This is the error I saw.
2. `echo 'CLOUD= $CLOUD'`: single quotes print `$CLOUD` literally. Double quotes expand it.
3. `[ $CLOUD = 'aws']`: `]` must be a separate word, so it needs a space before it. Without quotes, an empty `$CLOUD` would also break the test.
4. `] then`: `then` needs `;` or a new line before it. This is a parse error, so `sh` would not even have started the script once mistake 1 was fixed.

`cloud-init schema` could not catch any of these: the YAML was valid, and the script is just a string to it.

**Fix:** corrected the three lines (`CLOUD=$(...)`, `echo "Cloud= $CLOUD"`, `if [ "$CLOUD" = 'aws' ]; then`), added `ssh_pwauth: false`, deleted `devboxtest`, and committed the file as `a988013`. That commit then ran on AWS EC2 (`t4g.small`, `ap-southeast-1`): `status: done`, `extended_status: done`, no errors, and UFW showed the EC2 SSH rule. Details in the README section "Verified on AWS EC2".

**Prevention:** copy code changes instead of retyping them, then read `git diff` before launching. `cloud-init schema` checks the YAML only, so also check the shell: extract the `runcmd` script and run `sh -n` on it in the `lab` VM before every launch (this is the shell check I listed as a follow-up in #1). `set -u` did its job: like the guard in #2, it stopped the script before the firewall was enabled. A half-configured VM gets deleted and rebuilt, not patched. Firewall rules should not encode a guess about the network's shape; on a cloud, restrict SSH sources where the network is defined (the security group).

**Evidence:** [`docs/evidence/incident-6.txt`](evidence/incident-6.txt) (log tail, the generated script lines, the diff, the corrected lines and the EC2 result).

---

## #5: flask --app app could not find the Flask application
**Date:** 2026-11-06 | **Phase:** 2 | **Component:** Flask CLI (application discovery, Python imports) | **Time lost:** 15 min

**Symptom:** `flask --app app run` printed `Error: Failed to find Flask application or factory in module 'app'. Use 'app:name' to specify one.` The app code was in `app/app.py` and I ran the command from the repo root.

**Diagnosis:** Earlier in the same session, `flask` itself was `command not found` because the venv was not active in that terminal tab (no `(.venv)` in the prompt); activating it fixed that, and it is a separate problem. For this error I read the message, which says Flask imported a module called `app` and found no application in it. My layout has a **folder** `app/` containing a **file** `app.py`, so I checked what `--app app` would import. I then tried `flask app/app:app run`, which failed differently (`No such command 'app/app:app'`) because I had dropped the `--app` flag, so Flask read my string as a command name. The message `Use 'app:name'` pointed to the `module:variable` form.

**Root cause:** `--app app` makes Flask import the name `app`. From the repo root that name matches the folder `app/`, not the file inside it, and the folder has no Flask object. The Flask object is the variable `app` inside `app/app.py`. I checked this in the installed Flask source (`flask/cli.py`, `load_app` and `prepare_import`). `--app` is split at the colon. The part before it goes through `prepare_import`, which adds a folder to `sys.path` and returns a module name. For `--app app` it adds the repo root and returns `app`, which Python resolves to the folder `app/` (no `__init__.py`, so a namespace package), not to the file `app/app.py`. For `--app app/app:app` it adds the `app/` folder and returns `app`, which then resolves to `app/app.py`.

**Fix:** pointed Flask at the file and named the variable, with the flag in place: `flask --app app/app:app run`. The server started and `/health` returned 200.

**Prevention:** give `--app` an explicit `module:variable` so the folder and file cannot be confused, and check that the prompt shows `(.venv)` before running `flask`. The container will start gunicorn with a `module:variable` string too, so the same rule applies there. A folder and a file with the same name invite this mistake. Open decision: rename `app/app.py` so the folder and the file differ; I will decide when I write the Dockerfile, because gunicorn takes the same `module:variable` string.

**Evidence:** [`docs/evidence/incident-5.txt`](evidence/incident-5.txt) (the three error outputs and the working form).

---

## #4: Experiment: stopping docker.service did not stop Docker, the socket did
**Date:** 2026-11-05 | **Phase:** 1 | **Component:** systemd (docker.service, docker.socket) | **Time lost:** 30 min

**This was a deliberate experiment on a throwaway VM (`devboxtest`), not a surprise failure.** I stopped the Docker units in different combinations to see what `docker ps` does and what happens to containers with `--restart unless-stopped`.

**Symptom:** after `sudo systemctl stop docker.service`, `systemctl is-active docker.service` said `inactive`, but the next `docker ps` worked and the service was `active` again. Only after stopping both units did `docker ps` fail with `Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?`.

**Diagnosis:** Baseline: both units `active` and `enabled`, and `ss -xlnp` showed `/run/docker.sock` held by both `dockerd` and `systemd` (pid 1). Then, in order:
1. Stopped `docker.service` only. systemd warned `Stopping 'docker.service', but its triggering units are still active: docker.socket`. `docker ps` started the daemon again.
2. Stopped both units. `is-active` said `inactive` for both, `ss` showed no listener, and `docker ps` failed. `ls -l /var/run/docker.sock` still showed the socket file, so a leftover file does not mean something is listening.
3. Started both, then stopped `docker.socket` only. Afterwards both `docker` and `docker.socket` were `inactive` and `docker ps` failed, so stopping the socket also stopped the service. `systemctl cat docker.service` shows `Requires=docker.socket`, which explains it.
4. `is-enabled` stayed `enabled` for both units in every state.
5. Started two containers with `--restart unless-stopped`, stopped one by hand (`manual`), then stopped and started the Docker units. Only `keep` was running after the daemon came back.

**What I predicted wrong:** I predicted that stopping the socket would behave like stopping the service, with `docker ps` waking the daemon again. It does not, because with the socket stopped nothing listens on the path and nothing can start the daemon.

**Root cause:** Docker uses systemd socket activation. systemd owns the listening socket (`docker.socket`) and starts `docker.service` when a client connects, so stopping only the service is undone by the next `docker ps`. `docker.service` has `Requires=docker.socket`, so stopping the socket stops the service as well. `enabled` and `active` are separate: stopping a unit does not disable it, so it still comes up on the next boot. `unless-stopped` restarts a container when the daemon comes back, unless I stopped that container myself, which is why `manual` stayed `Exited` and `keep` came back.

**Fix:** nothing to fix, the system behaved as designed. I left the VM with both units started and removed the test containers (`keep`, `manual`).

**Prevention:** To stop Docker on purpose, stop `docker.socket` and `docker.service` together. Keeping it stopped across reboots is a separate step (`disable`). Do not use "`docker ps` works" as proof that nobody stopped Docker, because the socket can wake the service. In the Phase 4 deploy script, check the service state (`systemctl is-active docker`) separately from whether the API answers.

**Evidence:** [`docs/evidence/incident-4.txt`](evidence/incident-4.txt) (outputs from each step).

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
