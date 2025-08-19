
def test_import():
    import heas
    assert hasattr(heas, "simulate")
    assert hasattr(heas, "optimize")
    assert hasattr(heas, "evaluate")
