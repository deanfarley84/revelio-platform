"""Tests for the DATABASE_URL scheme rewrite logic."""
from app.core.database import _to_async_url


def test_postgresql_scheme_gets_asyncpg_driver():
    out = _to_async_url("postgresql://user:pw@host:5432/db")
    assert out == "postgresql+asyncpg://user:pw@host:5432/db"


def test_postgres_scheme_alias_is_handled():
    out = _to_async_url("postgres://user:pw@host:5432/db")
    assert out == "postgresql+asyncpg://user:pw@host:5432/db"


def test_postgres_substring_does_not_corrupt_postgresql():
    # Regression: a naive str.replace('postgres://', 'postgresql+asyncpg://')
    # turns 'postgresql://' into 'postgresqlql+asyncpg://' because
    # 'postgres://' is a substring of 'postgresql://'.
    out = _to_async_url("postgresql://u:p@h/d")
    assert "ql+asyncpg" not in out
    assert out.startswith("postgresql+asyncpg://")


def test_already_asyncpg_url_is_unchanged():
    url = "postgresql+asyncpg://u:p@h/d"
    assert _to_async_url(url) == url


def test_unknown_scheme_passes_through():
    url = "sqlite:///./test.db"
    assert _to_async_url(url) == url


def test_url_with_query_params_preserved():
    out = _to_async_url("postgres://u:p@h/d?sslmode=require")
    assert out == "postgresql+asyncpg://u:p@h/d?sslmode=require"
