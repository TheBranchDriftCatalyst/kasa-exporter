#!/usr/bin/env python3
"""Render every deployed Grafana panel with Playwright, recording errors and frames.

Requires the optional playwright package and its Chromium browser. Read-only;
uses the browser's existing anonymous/authenticated access, never edits dashboards.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from playwright.async_api import async_playwright


async def inspect_panel(page, base, dashboard, panel, output):
    errors, frames, pending = [], [], []
    device_ids = set()

    async def response_received(response):
        if "/api/ds/query" not in response.url:
            return
        try:
            data = await response.json()
            for ref, result in data.get("results", {}).items():
                if result.get("error"):
                    errors.append(f"{ref}: {result['error']}")
                for frame in result.get("frames", []):
                    fields = frame.get("schema", {}).get("fields", [])
                    values = frame.get("data", {}).get("values", [])
                    for field, column in zip(fields, values, strict=True):
                        if field.get("name") == "device_id":
                            device_ids.update(str(value) for value in column)
                    frames.append(
                        {
                            "ref": ref,
                            "fields": [
                                {"name": f["name"], "type": f["type"]}
                                for f in frame.get("schema", {}).get("fields", [])
                            ],
                            "rows": max(
                                (len(v) for v in frame.get("data", {}).get("values", [])),
                                default=0,
                            ),
                        }
                    )
        except Exception as error:
            errors.append(str(error))

    def schedule(response):
        pending.append(asyncio.create_task(response_received(response)))

    def page_error(error):
        errors.append(str(error))

    page.on("response", schedule)
    page.on("pageerror", page_error)
    item = {"uid": dashboard["uid"], "panel_id": panel["id"], "title": panel.get("title", "")}
    try:
        query = urlencode({"viewPanel": panel["id"], "from": "now-6h", "to": "now", "refresh": ""})
        await page.goto(
            f"{base}/d/{dashboard['uid']}?{query}", wait_until="networkidle", timeout=60000
        )
        content = page.locator('[data-testid="data-testid panel content"]')
        await content.wait_for(timeout=15000)
        body = await content.inner_text()
        for message in ("Data is missing", "An unexpected error", "Query error", "No field name"):
            if message.lower() in body.lower():
                errors.append(body)
        if pending:
            await asyncio.gather(*pending)
        if panel["type"] == "table":
            duplicates = [value for value in device_ids if body.count(value) > 1]
            if duplicates:
                errors.append(f"Table repeats {len(duplicates)} device IDs across rows")
        empty = panel["type"] != "text" and not any(f["rows"] for f in frames)
        name = f"{dashboard['uid']}-{panel['id']}"
        await page.screenshot(path=str(output / f"{name}.png"))
        (output / f"{name}.txt").write_text(body)
        item.update(
            status="FAIL" if errors else "EMPTY" if empty else "RENDERED",
            errors=errors,
            frames=frames,
            screenshot=f"{name}.png",
        )
    except Exception as error:
        item.update(status="FAIL", errors=[*errors, str(error)])
    finally:
        page.remove_listener("response", schedule)
        page.remove_listener("pageerror", page_error)
    return item


def panels(items):
    for panel in items:
        if panel["type"] != "row":
            yield panel
        yield from panels(panel.get("panels", []))


async def run(args):
    dashboards = []
    for file in sorted(args.dashboards.glob("*.json")):
        local = json.loads(file.read_text())
        uid = local["uid"]
        with urlopen(f"{args.grafana_url}/api/dashboards/uid/{uid}", timeout=30) as response:
            deployed = json.load(response)["dashboard"]

        def signature(dashboard):
            return {
                p["id"]: (p["type"], [t.get("expr") for t in p.get("targets", [])])
                for p in panels(dashboard.get("panels", []))
            }

        if signature(local) != signature(deployed):
            raise ValueError(
                f"{uid}: deployed panels differ from local JSON; wait for reconciliation"
            )
        dashboards.append(deployed)
    args.output.mkdir(parents=True, exist_ok=True)
    queue = asyncio.Queue()
    for dashboard in dashboards:
        for panel in panels(dashboard.get("panels", [])):
            queue.put_nowait((dashboard, panel))
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        async def worker():
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            while not queue.empty():
                dashboard, panel = queue.get_nowait()
                item = await inspect_panel(page, args.grafana_url, dashboard, panel, args.output)
                results.append(item)
                print(item["uid"], item["panel_id"], item["status"], flush=True)
                queue.task_done()
            await page.close()

        await asyncio.gather(*(worker() for _ in range(args.workers)))
        await browser.close()
    (args.output / "report.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(any(r["status"] == "FAIL" for r in results) or not results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grafana-url", default="http://grafana.talos00")
    parser.add_argument(
        "--dashboards",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "etc/grafana/provisioning/dashboards/dashboards",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3, choices=range(1, 5))
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
