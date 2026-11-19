import asyncio

import pytest

from kunpeng.clients.ozon import OzonPerformanceClient


@pytest.mark.asyncio
async def test_reports_for_same_credential_are_serialized(monkeypatch) -> None:
    active = 0
    maximum_active = 0

    async def fake_fetch(self, **kwargs):
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        await asyncio.sleep(0)
        active -= 1
        return {"ok": True}

    monkeypatch.setattr(
        OzonPerformanceClient,
        "_fetch_statistics_report_unlocked",
        fake_fetch,
    )
    first = OzonPerformanceClient("same-client", "secret-a")
    second = OzonPerformanceClient("same-client", "secret-b")

    await asyncio.gather(
        first.fetch_statistics_report(["1"], "2026-08-06", "2026-08-06"),
        second.fetch_statistics_report(["2"], "2026-08-06", "2026-08-06"),
    )

    assert maximum_active == 1
