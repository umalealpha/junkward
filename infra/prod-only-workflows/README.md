# Production-only workflows (parked)

Workflows in this folder are **not** run by GitHub Actions. They were moved out
of `.github/workflows/` in the test repository because they talk to the
production AWS account (EC2 Instance Connect into the omni host) and need
secrets this repository does not have. Left in place they failed on every
trigger and blocked Actions from being useful.

| File | What it does in production | Why parked here |
|---|---|---|
| `morning-check.yml` | 05:00 SAST daily: probes the live endpoints, SSHes to the host via AWS, runs `manage.py morning_check`, commits a report and opens Issues on red. | Needs AWS secrets and the prod host; probes the live site from a test repo. |

`.github/workflows/deploy.yml` stays where it is because the devlog guard
tests count it as a deploy path, but it is manual-only **and** gated on the
repository variable `ENABLE_AWS_DEPLOY` being `true`, so it cannot run here by
accident.

To restore production behaviour: move `morning-check.yml` back to
`.github/workflows/`, set `ENABLE_AWS_DEPLOY=true` under Settings ▸ Secrets and
variables ▸ Actions ▸ Variables, and add `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` as repository secrets.
