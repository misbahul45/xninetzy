from __future__ import annotations

import pytest


@pytest.fixture
def remoteok_html():
    return """
    <html><body>
    <div id="jobs">
      <div class="job">
        <a class="preventLink" href="/remote-jobs/remote-senior-backend-engineer-acme-100">
          <h2 itemprop="title">Senior Backend Engineer (Acme)</h2>
        </a>
        <div class="company">Acme Corp</div>
        <div class="tags">
          <span class="tag">python</span>
          <span class="tag">fastapi</span>
          <span class="tag">backend</span>
        </div>
        <span class="time">2026-09-20</span>
        <div class="description">We need a Python FastAPI backend dev with PostgreSQL.</div>
      </div>
      <div class="job">
        <a class="preventLink" href="/remote-jobs/remote-frontend-intern-gigacorp-200">
          <h2 itemprop="title">Frontend Developer Intern (GigaCorp)</h2>
        </a>
        <div class="company">GigaCorp</div>
        <div class="tags">
          <span class="tag">frontend</span>
          <span class="tag">react</span>
          <span class="tag">internship</span>
        </div>
        <span class="time">2026-09-19</span>
        <div class="description">Looking for a React intern to join our frontend team.</div>
      </div>
      <div class="job">
        <a class="preventLink" href="/remote-jobs/remote-product-manager-data-scientist-shop-300">
          <h2 itemprop="title">Senior Data Scientist (ShopCo)</h2>
        </a>
        <div class="company">ShopCo</div>
        <div class="tags">
          <span class="tag">data</span>
          <span class="tag">ml</span>
        </div>
        <span class="time">2026-09-15</span>
        <div class="description">Data scientist role working on recommendations.</div>
      </div>
    </div>
    </body></html>
    """


@pytest.fixture
def arbeitnow_html():
    return """
    <html><body>
    <div class="list-section">
      <div class="job">
        <a href="/jobs/python-intern-berlin-500">Python Intern (StartupX)</a>
        <div class="company">StartupX</div>
        <div class="location">Berlin</div>
        <div class="tags"><span>Python</span><span>Internship</span></div>
        <p>Looking for a Python intern to join our team in Berlin.</p>
      </div>
      <div class="job">
        <a href="/jobs/senior-backend-600">Senior Backend Engineer (BigCo)</a>
        <div class="company">BigCo</div>
        <div class="location">Remote</div>
        <div class="tags"><span>Node</span><span>Senior</span></div>
        <p>Senior backend position requiring 5+ years experience.</p>
      </div>
    </div>
    </body></html>
    """


@pytest.fixture
def fake_session():
    from xninetzy.os.research.sources.browser_session import FakeBrowserSession

    def _factory():
        return FakeBrowserSession

    return _factory


def test_matches_query_returns_true_for_single_token_in_haystack():
    from xninetzy.os.research.sources.query_match import matches_query

    assert matches_query("intern", "frontend developer intern gigacorp")
    assert matches_query("python", "we are looking for a python intern")


def test_matches_query_returns_false_for_missing_token():
    from xninetzy.os.research.sources.query_match import matches_query

    assert not matches_query("rust", "we are looking for a python intern")


def test_matches_query_uses_or_semantics_for_multi_token_query():
    from xninetzy.os.research.sources.query_match import matches_query

    assert matches_query("python intern", "we need a python intern")
    assert not matches_query("python intern", "we need a senior backend engineer role")
    assert matches_query("intern backend", "we need a backend engineer")
    assert matches_query("intern backend", "frontend intern gigacorp team")
    assert matches_query("intern backend", "looking for a python backend intern")
    assert not matches_query("rust cobol", "python backend dev")


def test_matches_query_empty_query_returns_true():
    from xninetzy.os.research.sources.query_match import matches_query

    assert matches_query("", "any haystack at all")
    assert matches_query("   ", "any haystack at all")
    assert matches_query(None, "any haystack at all")  # type: ignore[arg-type]


def test_matches_query_case_insensitive():
    from xninetzy.os.research.sources.query_match import matches_query

    assert matches_query("PYTHON", "we need a python dev")
    assert matches_query("Intern", "Looking for an Intern")
    assert matches_query("Backend", "BACKEND engineer wanted")


def test_matches_query_partial_token_does_not_match():
    from xninetzy.os.research.sources.query_match import matches_query

    assert not matches_query("inter", "frontend developer intern gigacorp")


def test_matches_query_returns_false_for_empty_haystack():
    from xninetzy.os.research.sources.query_match import matches_query

    assert not matches_query("intern", "")


def test_remoteok_returns_python_intern_via_or_match(remoteok_html, monkeypatch, tmp_path):
    import json
    import httpx

    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "x.sqlite3"))
    from xninetzy.core.config import get_settings
    get_settings.cache_clear()
    from xninetzy.db.sqlite import init_db
    init_db()

    class _FakeResp:
        def __init__(self, text):
            self.text = text
            self.status_code = 200

        def raise_for_status(self):
            return None

    payload = json.loads(
        '[{"id":100,"position":"Senior Backend Engineer (Acme)","company":"Acme","tags":["python","fastapi","backend"],"description":"Python FastAPI backend dev with PostgreSQL.","legal":null},'
        '{"id":200,"position":"Frontend Developer Intern (GigaCorp)","company":"GigaCorp","tags":["frontend","react","internship"],"description":"React intern to join frontend team.","legal":null},'
        '{"id":300,"position":"Senior Data Scientist (ShopCo)","company":"ShopCo","tags":["data","ml"],"description":"Data scientist recommendations.","legal":null}]'
    )

    async def _fake_get(self, url, headers=None):
        return _FakeResp(json.dumps(payload))

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    from xninetzy.os.research.sources.remoteok import RemoteOkAdapter
    import asyncio

    adapter = RemoteOkAdapter()
    records = asyncio.run(adapter.search("python intern", limit=10))
    titles = {r.title for r in records}
    assert "Senior Backend Engineer (Acme)" in titles
    assert "Frontend Developer Intern (GigaCorp)" in titles
    assert "Senior Data Scientist (ShopCo)" not in titles
    get_settings.cache_clear()


def test_remoteok_excludes_irrelevant_jobs_with_no_overlap(remoteok_html, monkeypatch, tmp_path):
    import json
    import httpx

    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "x.sqlite3"))
    from xninetzy.core.config import get_settings
    get_settings.cache_clear()
    from xninetzy.db.sqlite import init_db
    init_db()

    class _FakeResp:
        def __init__(self, text):
            self.text = text
            self.status_code = 200

        def raise_for_status(self):
            return None

    payload = json.loads(
        '[{"id":100,"position":"Backend Engineer","company":"Acme","tags":["python","backend"],"description":"Python dev","legal":null}]'
    )

    async def _fake_get(self, url, headers=None):
        return _FakeResp(json.dumps(payload))

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    from xninetzy.os.research.sources.remoteok import RemoteOkAdapter
    import asyncio

    adapter = RemoteOkAdapter()
    records = asyncio.run(adapter.search("rust", limit=10))
    assert records == []
    get_settings.cache_clear()


def test_arbeitnow_returns_python_intern_via_or_match(arbeitnow_html, monkeypatch, tmp_path):
    import json
    import httpx

    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "x.sqlite3"))
    from xninetzy.core.config import get_settings
    get_settings.cache_clear()
    from xninetzy.db.sqlite import init_db
    init_db()

    class _FakeResp:
        def __init__(self, text):
            self.text = text
            self.status_code = 200

        def raise_for_status(self):
            return None

    payload = json.dumps(
        {"data": [
            {"slug": "python-intern-berlin-500", "title": "Python Intern (StartupX)", "company_name": "StartupX", "tags": ["Python", "Internship"], "description": "Python intern in Berlin", "remote": False},
            {"slug": "senior-backend-600", "title": "Senior Backend Engineer (BigCo)", "company_name": "BigCo", "tags": ["Node", "Senior"], "description": "Senior backend role", "remote": True},
        ]}
    )

    async def _fake_get(self, url, params=None):
        return _FakeResp(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    from xninetzy.os.research.sources.arbeitnow import ArbeitNowAdapter
    import asyncio

    adapter = ArbeitNowAdapter()
    records = asyncio.run(adapter.search("python intern", limit=10))
    titles = {r.title for r in records}
    assert "Python Intern (StartupX)" in titles
    assert "Senior Backend Engineer (BigCo)" not in titles
    get_settings.cache_clear()
