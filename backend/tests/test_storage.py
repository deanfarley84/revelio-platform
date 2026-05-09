"""Tests for storage local-fallback selection logic."""
import os
from unittest.mock import patch
from app.services import storage


def test_use_local_when_aws_keys_empty():
    with patch.object(storage.settings, "AWS_ACCESS_KEY_ID", ""), \
         patch.object(storage.settings, "AWS_SECRET_ACCESS_KEY", ""):
        assert storage.use_local() is True


def test_use_local_when_explicit_env_set(monkeypatch):
    monkeypatch.setenv("USE_LOCAL_STORAGE", "true")
    with patch.object(storage.settings, "AWS_ACCESS_KEY_ID", "AKIA..."), \
         patch.object(storage.settings, "AWS_SECRET_ACCESS_KEY", "secret"):
        assert storage.use_local() is True


def test_use_s3_when_keys_present(monkeypatch):
    monkeypatch.delenv("USE_LOCAL_STORAGE", raising=False)
    with patch.object(storage.settings, "AWS_ACCESS_KEY_ID", "AKIA..."), \
         patch.object(storage.settings, "AWS_SECRET_ACCESS_KEY", "secret"):
        assert storage.use_local() is False
