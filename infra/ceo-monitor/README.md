# CEO Omni Brief — engine

The daily "CEO Omni Brief" (and the Sunday board read) that reach the CEO,
cc the CFO. Live copies run from **`/opt/ceo-monitor/` on the omni host**, NOT
from this directory.

| file | what it does |
|---|---|
| `run.sh` | cron entry point: copies `ceo_engine.py` into the backend container, pipes `ceo_driver.py` into `manage.py shell` |
| `ceo_driver.py` | gathers the data (mail, meetings, tasks) and calls the engine |
| `ceo_engine.py` | scores/renders the HTML |
| `ceo_sunday_driver.py`, `run_sunday.sh` | the Sunday board read |
| `cfo_driver.py`, `run_cfo.sh` | the CFO's own morning brief (same engine, his mailbox) |

Cron (host, not in `install-crons.sh`):

    /etc/cron.d/ceo-brief        30 4 * * *  -> run.sh
    /etc/cron.d/ceo-board-read    0 5 * * 0  -> run_sunday.sh
    /etc/cron.d/cfo-brief        35 4 * * *  -> run_cfo.sh

`install-crons.sh` only ever DELETES an active file for a job it lists as
DISABLED, so these host-only jobs are safe from it — but they are also not
managed by it, which is why a change here has to be copied to the host by hand
(see "Deploying a change" below).

The CFO brief runs five minutes after the CEO brief on purpose: both read the
same note table, and staggering them keeps two `docker compose exec` runs off
the same second.

MAILBOX CREDENTIALS DIFFER, and this is easy to get wrong:
  * `run.sh`     -> CEO_GRAPH_*    (from /opt/ceo-monitor/graph.env) -> aiyer@
  * `run_cfo.sh` -> GRAPH_READER_* (already in the container env)    -> pganesharajah@
The tenant's app-only access policy scopes GRAPH_READER_* to pganesharajah@ and
nothing else — excoboard@ and omni@ return "Blocked by tenant configured
AppOnly AccessPolicy settings". Do not point either driver at another mailbox
expecting it to work.

## Why these files are in the repo

Until 2026-08-21 they existed **only** on the host, versioned by `.bak.<date>`
copies and hand-deployed. Nothing tested them, `install-crons.sh` did not manage
them, and a rebuild would have lost them. The copies here were taken from prod
and verified byte-identical by md5:

    ceo_driver.py         d126c8b651ace772924ccc27c40f7020  (pre-patch)
    ceo_engine.py         8c44496fc5f53ef685841a6448a78645
    ceo_sunday_driver.py  508fd507ab9b5c9b52be2aa1951042d0
    run.sh                60eb7f2e8d988f07942a0584ba5cde43
    run_sunday.sh         18a963b8b67d80f6eef853847f422783

`graph.env` (the Microsoft Graph client secret) is deliberately NOT here and
must never be committed. It stays at `/opt/ceo-monitor/graph.env` on the host.

## Deploying a change

These do not ride the normal image build — copy them to the host:

    sudo cp infra/ceo-monitor/ceo_driver.py /opt/ceo-monitor/ceo_driver.py

Business rules belong in the Django app where they can be tested, not in these
files. `fetch_waiting_on_ceo` calls
`hris.exec_signoff_service.is_routine_signoff_task`, which has tests in
`hris/tests/test_signoff_sibling_tasks.py`; the inline fallback there exists
only so an older backend image cannot kill the 04:30 brief on an import error.
