from korpa_api.database import async_database_url
from pytest import MonkeyPatch
from sqlalchemy.engine import make_url


def test_async_url_accepts_hosted_ssl_parameters(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/korpa?sslmode=require&channel_binding=require",
    )
    url = make_url(async_database_url())
    assert url.drivername == "postgresql+asyncpg"
    assert dict(url.query) == {"ssl": "require"}
    assert url.password == "p"


def test_async_url_without_ssl_stays_plain(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://korpa:korpa@localhost:5432/korpa")
    assert make_url(async_database_url()).query == {}
