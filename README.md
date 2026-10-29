# devops-project

A self-directed learning project: a tested Flask app, packaged in Docker, built by GitHub Actions and deployed automatically to a Linux VM that I provision with code, with monitoring on top.

I am building it phase by phase to learn DevOps fundamentals, and I keep notes on everything that breaks in [`docs/incident-log.md`](docs/incident-log.md).

## Status (updated October 29, 2026)

| Phase | What | Status |
|---|---|---|
| 1 | Self-configuring server (cloud-init, Docker, UFW, SSH key) | In progress |
| 2 | Containerize the Flask app | Not started |
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

## Repository layout

```
app/                  Flask app and tests (planned)
Dockerfile            Phase 2 (planned)
cloud-init.yaml       Phase 1 (in progress)
deploy/               Phase 4 (planned)
.github/workflows/    Phase 3 (planned)
terraform/            Phase 5 (planned)
monitoring/           Phase 6 (planned)
docs/                 incident log, architecture diagram
```

## Notes

- This is a learning project. Decisions and mistakes are documented rather than hidden.
- No secrets are stored in this repository.
