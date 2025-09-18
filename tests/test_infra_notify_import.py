import importlib

def test_import_infra_notify_module():
    mod = importlib.import_module("src.infra.notify")
    assert mod is not None
