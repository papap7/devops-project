# devops-project

A self-directed learning project: a tested Flask app, packaged in Docker, built by GitHub Actions and deployed automatically to a Linux VM that I provision with code, with monitoring on top.

I am building it phase by phase to learn DevOps fundamentals, and I keep notes on everything that breaks in [`docs/incident-log.md`](docs/incident-log.md).

## Status (updated November 11, 2026)

| Phase | What | Status |
|---|---|---|
| 1 | Self-configuring server (cloud-init, Docker, UFW, SSH key) | Done ([evidence](docs/evidence/phase1.md)); also verified on AWS EC2 ([evidence](docs/evidence/ec2-raw.txt)) |
| 2 | Containerize the Flask app | In progress: Flask app with `/health` and `/version` runs locally ([evidence](docs/evidence/phase2.md)); Dockerfile next |
| 3 | CI with GitHub Actions (test, build, push to GHCR) | Not started |
| 4 | Automated deployment (pull-based, health check, rollback) | Not started |
| 5 | Infrastructure as code with Terraform | Not started |
| 6 | Monitoring (Prometheus, Grafana), docs, demo | Not started |

Planned finish: December 1, 2026.

## Planned architecture

- **Server:** Ubuntu 24.04 VM on my Mac (Multipass), configured on first boot by a cloud-init file
- **App:** Flask served by gunicorn in a container, with `/health` and `/version` endpoints
- **CI:** GitHub Actions runs tests, builds an arm64 image and publishes it to GitHub Container Registry, tagged with the commit SHA
- **CD:** a systemd timer on the VM pulls the new image, health-checks it and rolls back if it fails
- **IaC:** Terraform (Docker provider) manages the monitoring stack
- **Monitoring:** Prometheus, Grafana and cAdvisor with one tested alert rule

## Why a local VM

I chose to run everything locally so the project costs nothing and does not depend on any cloud account. The pieces map to cloud services, and I will document that mapping in this README when the project is further along.

## Verified on AWS EC2

On November 11, 2026 I launched the same `cloud-init.yaml` (commit [`a988013`](https://github.com/papap7/devops-project/commit/a988013)) as EC2 user data. Nothing was done by hand after launch, and the instance was terminated after the test.

| Item | Result |
|---|---|
| Instance | `t4g.small` (AWS Graviton, arm64, 2 vCPU, 2 GiB), Ubuntu Server 24.04 LTS |
| Region | `ap-southeast-1` (Singapore) |
| Launch to cloud-init done | 110 s on EC2; 82.5 s on my local Multipass VM, same commit |
| Checks | `status: done` with no errors; `docker run hello-world` (arm64); UFW active; SSH key login works, password login refused |
| Network | The security group allows only SSH, only from my IP; UFW denies all other incoming traffic |

Before the first launch I found that my UFW rule would have locked me out on EC2: it allowed SSH only from the VM's default gateway, which is my Mac on Multipass but the VPC router on EC2. The file now checks the platform with `cloud-init query v1.cloud_name` and, on AWS, leaves the source restriction to the security group. See [incident #6](docs/incident-log.md).

Evidence: [`docs/evidence/ec2-raw.txt`](docs/evidence/ec2-raw.txt) (all command output) and [`docs/evidence/img/`](docs/evidence/img/) (console screenshots).

## Repository layout

```
app/                  Flask app with /health and /version (Phase 2, in progress; tests planned)
Dockerfile            Phase 2 (planned)
cloud-init.yaml       Phase 1 (done)
deploy/               Phase 4 (planned)
.github/workflows/    Phase 3 (planned)
terraform/            Phase 5 (planned)
monitoring/           Phase 6 (planned)
docs/                 incident log and evidence for each phase
```

## Notes

- This is a learning project. Decisions and mistakes are documented rather than hidden.
- No secrets are stored in this repository.
