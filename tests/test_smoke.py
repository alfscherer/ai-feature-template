def test_smoke() -> None:
    """Verifies the test runner and package layout are wired up correctly."""
    import app

    assert app is not None
