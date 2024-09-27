from contextlib import contextmanager
from pathlib import Path
from wex.response import Response
from wex.sitemaps import urls_from_sitemaps


@contextmanager
def relative_resource_stream(resource):
    ref = Path(__file__).parent / resource
    with ref.open('rb') as readable:
        yield readable



def response(resource):
    with relative_resource_stream(resource) as readable:
        response = Response.from_readable(readable)
    return response


def test_urls_from_robots_txt():
    src = response('fixtures/robots_txt')
    items = list(urls_from_sitemaps(src))
    url = 'http://sitemap.foo.com/SiteMap/sitemap_index.xml.gz#{"sitemap":true}'
    assert items == [('url', url)]


def test_urls_from_sitemap_index_xml():
    src = response('fixtures/sitemap_index_xml')
    items = list(urls_from_sitemaps(src))
    # wex.sitemaps.urls_from_sitemap_or_sitemapindex sets a fragment
    # in case we need to try and process an Atom, RSS or text file
    url0 = 'http://sitemap.foo.com/SiteMap/sitemap_0.xml.gz#{"sitemap":true}'
    url1 = 'http://sitemap.foo.com/SiteMap/sitemap_1.xml.gz#{"sitemap":true}'
    assert items == [('url', url0), ('url', url1)]


def test_non_sitemap_xml():
    src = response('fixtures/other_xml')
    items = list(urls_from_sitemaps(src))
    assert items == []
