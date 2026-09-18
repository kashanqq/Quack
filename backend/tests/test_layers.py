"""Shared B3 entry points remain importable before B1/B2 are merged."""

import importlib


def test_b3_shared_modules_import_without_b1_or_b2():
    for module in (
        "app.config",
        "app.keys",
        "app.errors",
        "app.api.deps",
        "app.api.auth",
        "app.main",
    ):
        importlib.import_module(module)
