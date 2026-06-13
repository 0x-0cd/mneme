"""Smoke test: verify package imports correctly."""


def test_import():
    import mneme  # noqa: F811

    assert mneme.__version__ == "0.1.0"
