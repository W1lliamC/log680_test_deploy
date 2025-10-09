import importlib

def test_config_imports():
    cfg = importlib.import_module("config")
    assert hasattr(cfg, "Settings") or hasattr(cfg, "load_settings")
