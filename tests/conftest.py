from pathlib import Path
import pytest


@pytest.fixture
def testme(monkeypatch):
    """ Add fixtures/TestMe.egg to sys.path """
    here = Path(__file__).parent
    path = here.joinpath('fixtures/TestMe.egg')
    monkeypatch.syspath_prepend(path)
    import testme
    return testme
