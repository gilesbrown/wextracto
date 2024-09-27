# coding: utf-8
from __future__ import unicode_literals
import codecs
import pytest
from pathlib import Path
from contextlib import contextmanager
from six.moves.http_client import BadStatusLine
from six import BytesIO
from wex.response import Response, DEFAULT_READ_SIZE

utf8_reader = codecs.getreader('UTF-8')

with_content_length = '''{protocol_version} {code} {reason}\r
Content-length: {content_length}\r
\r
{content}'''

without_content_length = '''HTTP/1.1 200 OK\r
\r
{content}'''

content = 'HELLO'

@contextmanager
def relative_resource_stream(resource):
    ref = Path(__file__).parent / resource
    with ref.open('rb') as readable:
        yield readable


def build_response(content, response=with_content_length, **kw):

    fmt = {
        'content': content,
        'content_length': len(content),
        'protocol_version': 'HTTP/1.1',
        'code': 200,
        'reason': 'OK',
    }

    for k in fmt:
        if k in kw:
            fmt[k] = kw.pop(k)

    response_bytes = response.format(**fmt).encode('utf-8')
    return Response.from_readable(BytesIO(response_bytes), **kw)


def test_read():
    response = build_response(content)
    assert utf8_reader(response).read() == content
    assert response.geturl() == None
    # the other attributes don't have accessors
    assert response.protocol == 'HTTP'
    assert response.version == (1, 1)
    assert response.code == 200
    assert response.reason == 'OK'
    assert response.request_url == None
    assert response.warc_protocol == None
    assert response.warc_version == None
    assert response.warc_headers == None


def test_read_seek_read():
    response = build_response(content)
    assert utf8_reader(response).read() == content
    response.seek(0)
    assert utf8_reader(response).read() == content


def test_unexpected_keyword_argument():
    with pytest.raises(TypeError):
        build_response(content, foo='bar')


def test_read_no_content_length():
    response = build_response(content, without_content_length)
    assert utf8_reader(response).read() == content


def test_read_negative_content_length():
    response = build_response(content, content_length='-1')
    assert utf8_reader(response).read() == content


def test_read_non_integer_content_length():
    response = build_response(content, content_length='X')
    assert utf8_reader(response).read() == content


def test_read_large_content():
    large_content = 'X' * DEFAULT_READ_SIZE * 2
    response = build_response(large_content, without_content_length)
    assert utf8_reader(response).read() == large_content


def test_read_non_integer_code():
    with pytest.raises(BadStatusLine):
        build_response(content, code='X')


def test_read_bad_protocol_version():
    with pytest.raises(BadStatusLine):
        build_response(content, protocol_version='HTTP/X')


def test_extract_from_readable():
    readable = BytesIO(b'FTP/1.0 200 OK\r\n\r\nhello')
    def extract(src):
        yield (src.read(),)
    values = list(Response.values_from_readable(extract, readable))
    assert values == [(b'hello',)]


def test_undecodable_url():
    with relative_resource_stream('fixtures/undecodable_url.wexin_') as readable:
        response = Response.from_readable(readable)
        assert response.url == 'https://www.example.net/Ã'
        assert response.request_url == 'https://www.example.net/Ã#{"method":"get"}'


def test_warc_response():
    with relative_resource_stream('fixtures/warc_response') as readable:
        response = Response.from_readable(readable)
        assert response.url == 'http://httpbin.org/get?this=that'
        assert response.warc_protocol == b'WARC'
        assert response.warc_version == (1, 0)
        assert response.warc_headers.get('warc-type') == 'response'
