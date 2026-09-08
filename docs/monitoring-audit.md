# Kasa monitoring audit — 2026-09-08

The exporter now collects all five KP125M plugs. The six Kasa dashboards were
reviewed panel by panel, their queries executed against Mimir, and their deployed
panels rendered in Grafana. This audit covers this repository, not every dashboard
in the homelab.

## Verified results

- Six dashboards, 158 panels, 236 panel targets, and two enabled Prometheus annotations.
- Every panel rendered without errors with all devices and with one selected device.
- Collection, recording-rule health, duplicate-series checks, percentage totals,
  cost-rate rounding consistency, and recording freshness passed.
- 120 Python tests passed; three credential-dependent tests were skipped. Promtool
  fixtures and repository-configured lint/type checks passed.
- Empty results remain explicit: new historical windows, forecast warmup,
  unobserved tariff periods, and inactive conditions. See the per-panel evidence.

## Deployment failure

The plugs now announce the TPAP protocol. The previous python-kasa dependency
silently omitted unsupported devices, leaving an HTTP-healthy exporter with no
measurements. Read-only discovery identified five affected plugs; authenticated
read-only updates confirmed the protocol fix before deployment. No relays were
switched and no credentials were changed.

Production pins an image digest and the python-kasa dependency pins
[upstream PR 1592](https://github.com/python-kasa/python-kasa/pull/1592) at commit
`e7084472972f08f2e2235b342f3964aedbfaeb3b`. This is an unreleased upstream patch;
replacing it with a supported release is tracked in homelab issue `TALOS-ss7f`.
The upstream transport's 116 unit tests passed before adoption.

Readiness now requires fresh device measurements. Unsupported-device counts,
discovery completion, measurement age, and fresh-device counts are exported.
Failed/stale devices and obsolete tariff labels are removed from the registry.
The deployment does not mount a Kubernetes API token or retain `NET_RAW`.
LAN broadcast discovery still requires host networking.

## Mathematical and visualization corrections

- Cost is an hourly rate gauge. Historical cost integrates that rate at 30-second
  intervals; it does not apply `increase()` to a gauge or sum dollars/hour as dollars.
- Sampled integrals subtract the final endpoint to avoid counting both ends of an
  interval. Missing periods are not extrapolated into a full day or month.
- Zero/missing comparison baselines produce no percentage, rather than NaN.
- Filters use the [Prometheus datasource default formatting](https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/variable-syntax/);
  generic regex formatting would under-escape dotted version values in PromQL.
- Device daily/monthly energy is already kWh. Units and table-column units now
  distinguish power, energy, hourly cost, tariffs, percentages, and runtime.
- Aggregations deduplicate scrape instances by device ID and retain version.
  Aliases are display names, not unique identities. Device tables merge into one
  row per device instead of splitting power and cost into separate rows.
- Tariff-label joins use a unit mask, avoiding multiplication by the price twice.
  Seasonal scenarios use the exporter configuration rather than hard-coded prices.
- Tariff season and interval boundaries use the utility timezone. Intervals are
  start-inclusive/end-exclusive; DST transition tests cover the next-change timer.
- Utilization is a share of power. “Efficiency” panels now state that they show
  implied tariffs. Constant-load forecasts are labeled as projections, not bills.
- Peak battery sizing uses the peak of aggregate load, not the sum of unrelated
  per-device peaks. Charge curves, charge times, efficiency losses, and the
  selected discharge floor use consistent energy accounting.
- Linear forecasts require 80% training-window coverage before display.
- Fake correlation, heatmaps without histogram data, fixed next-rate timers, and
  incident-log claims were removed or replaced with accurately named views.
- Anomaly indicators are Boolean; sampled breach counts are not incident counts.
  Missing readings do not map to “healthy.” Unused dashboard controls were removed.
- Recording rules and scraping both use 30-second intervals. Corrected recordings
  use the `kasa:` prefix so old incorrect derived history is not mixed into them.

The dashboards show fresh collection and 24-hour recording coverage at the top.
Low coverage means historical totals are partial. Coverage measures available total
recordings; it does not prove every device contributed to every sample.

## Repeatable checks

From the repository root, with dependencies installed:

```bash
poetry run pytest -q
promtool test rules tests/monitoring-rules.yml
python scripts/audit_dashboard_queries.py --output /tmp/kasa-queries.json
python scripts/audit_dashboard_queries.py \
  --hours 1 --var version=1.0.0 --var 'device=Dream Machine' \
  --var 'baseline_device=Dream Machine' --output /tmp/kasa-filtered.json
```

The query auditor walks every target, including hidden targets and nested panels.
It resolves variables, chooses instant/range requests, checks label contracts,
duplicate label sets, numeric bounds, NaN/infinity, collection health, and rule
health. It also checks enabled Prometheus annotations, duplicate device series,
power shares, cost-rate rounding consistency, and recording freshness. It writes
a per-target JSON report. It exits nonzero for `FAIL` **or EMPTY**;
expected missing history is deliberately not disguised as a pass.

Rendering uses optional Playwright and Chromium:

```bash
uv run --with playwright python -m playwright install chromium
uv run --with playwright python scripts/audit_dashboard_rendering.py \
  --output /tmp/kasa-rendering
uv run --with playwright python scripts/audit_dashboard_rendering.py \
  --var version=1.0.0 --var 'device=Dream Machine' \
  --var 'baseline_device=Dream Machine' --output /tmp/kasa-rendering-filtered
```

The browser auditor first checks that deployed panel IDs/types/expressions match
the local JSON. It renders each individual panel, captures query-frame schemas,
checks browser/backend errors and repeated device rows, and saves screenshots.
`RENDERED` means rendering succeeded; it does not prove arbitrary formula semantics.
`EMPTY` means no populated query frames. Query reports retain individual empty
series even when other series allow the same panel to render.

The committed [per-panel evidence](dashboard-audits/panel-review-2026-09-08.json)
combines the query, filter, and browser outcomes. The fixtures independently prove
known-load cost integration, duplicate-scrape handling, duplicate aliases,
percentage totals, zero-variance anomalies, battery energy balance, and collection
health alerts. CI runs the Python tests and promtool fixtures.

## Deployment and interpretation

Dashboard URLs in `k8s/grafana-dashboards.yaml` pin an immutable content commit.
When changing dashboard JSON, first commit/push it, then update those URL revisions
and reconcile ArgoCD. This avoids stale content from the moving GitHub `main` URL.
The browser audit refuses to validate an older deployed definition.

Seven-/30-day offset comparisons and coarse historical record panels need new
history after the cutover. Tariff periods not yet observed and inactive threshold
conditions can also have empty results. A solar-assisted runtime is intentionally
undefined when modeled average generation covers the selected load. These cases
are recorded explicitly in the audit evidence.

Costs exclude taxes and other bill charges and use the configured utility plan;
the plan was not verified against a utility bill. Battery and solar panels model
selected assumptions, not real battery/solar telemetry. Query success, snapshots,
and fixtures provide bounded evidence, not a proof of every future input or outage.

The existing exploded-source/Vite development migration was left intact in the
original dirty checkout. Its legacy build paths are not the audited source of
truth; use the six canonical JSON files above. Completing that migration is tracked
as `TALOS-oq7x` in homelab beads.
