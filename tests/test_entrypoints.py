import pytest
from pathlib import Path
from importlib import import_module
from contextlib import contextmanager
from wex.response import Response
from wex.entrypoints import extractor_from_entry_points


here = Path(__file__).parent


@contextmanager
def local_resource_stream(resource):
    ref = here.joinpath(resource)
    with ref.open('rb') as fp:
        yield fp


def test_extractor_from_entry_points(testme):
    extract = extractor_from_entry_points()
    with local_resource_stream('fixtures/get_this_that') as readable:
        for _ in Response.values_from_readable(extract, readable):
            pass
    hostname = 'httpbin.org'
    assert list(extract.extractors.keys()) == [hostname]
    extractors = set(extract.extractors[hostname].extractors)
    expected = set([testme.example, testme.example_with_hostname_suffix])
    assert expected.issubset(extractors)


class FakeLogger(object):

    def __init__(self, name):
        self.name = name
        self.exceptions = []

    def exception(self, *args, **kwargs):
        self.exceptions.append((args, kwargs))

    # We need these addHandler/removeHandler pair now
    # because it seems like a new logging.getLogger()
    # call has been added into the entry point core code.

    def addHandler(self, handler):
        assert handler

    def removeHandler(self, handler):
        assert handler

    # Now we also may be asked for a root logger

    def getLogger(self, name="__root__"):
        assert name in (self.name, "__root__")
        return self


def extract_with_monkeypatched_logging(monkeypatch, excluded=[]):
    logger = FakeLogger('wex.entrypoints')
    monkeypatch.setattr('logging.getLogger', logger.getLogger)
    extractor = extractor_from_entry_points()
    with local_resource_stream('fixtures/robots_txt') as readable:
        for _ in Response.values_from_readable(extractor, readable):
            pass
    return logger


def test_extractor_from_entry_points_resolve_error(testme, monkeypatch):
    excluded = []
    logger = extract_with_monkeypatched_logging(monkeypatch, excluded)
    assert len(logger.exceptions) == 1
    assert logger.exceptions[0][0][0].startswith("Failed to resolve")


#def test_extractor_from_entry_points_excluded(monkeypatch):
#    excluded = ['nosuch']
#    logger = extract_with_monkeypatched_logging(monkeypatch, excluded)
#    assert len(logger.exceptions) == 0


def test_extractor_from_entry_points_hostname_suffix_excluded(testme):
    extractor = extractor_from_entry_points()
    with local_resource_stream('fixtures/robots_txt') as readable:
        for value in Response.values_from_readable(extractor, readable):
            pass
    hostname = 'www.foo.com'
    assert list(extractor.extractors.keys()) == [hostname]
    extractors = set(extractor.extractors[hostname].extractors)
    assert testme.example_with_hostname_suffix not in extractors
    assert testme.example in extractors


