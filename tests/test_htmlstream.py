# coding=utf-8
from __future__ import unicode_literals
import codecs
import pytest
from contextlib import contextmanager
from pathlib import Path
from six import text_type
from wex.response import Response
from wex.htmlstream import HTMLStream


@contextmanager
def stream_from_fixture(fixture):
    here = Path(__file__).parent
    resource = here / 'fixtures/htmlstream' / fixture
    with resource.open('rb') as readable:
        response = Response.from_readable(readable)
        # do a read just to make sure that we seek(0)
        response.read(100)
        yield HTMLStream(response)


def test_htmlstream():
    with stream_from_fixture('ascii') as stream:
        assert stream.declared_encodings == []
        text = stream.read()
        assert isinstance(text, text_type)
        assert text == '<p>just ASCII</p>\n'


def test_htmlstream_unicode():
    with stream_from_fixture('utf-8') as stream:
        assert stream.declared_encodings == []
        text = stream.read()
        assert isinstance(text, text_type)
        assert text == '<p>©<p>\n'


def test_htmlstream_utf8_bom():
    with stream_from_fixture('utf-8-with-bom') as stream:
        assert stream.declared_encodings == [('bom', 'utf-8')]
        assert stream.bom == codecs.BOM_UTF8
        text = stream.read()
        assert isinstance(text, text_type)
        assert text == '<p>©<p>\n'


def test_htmlstream_utf16_le_bom():
    with stream_from_fixture('utf-16-le-with-bom') as stream:
        assert stream.declared_encodings == [('bom', 'utf-16-le')]
        assert stream.bom == codecs.BOM_UTF16_LE
        text = stream.read()
        assert stream.encoding == 'utf-16-le'
        assert isinstance(text, text_type)
        assert text == 'Hello'


def test_htmlstream_meta_charset():
    with stream_from_fixture('shift-jis-meta-charset') as stream:
        assert stream.declared_encodings == [('http-content-type', 'ISO-8859-1'),
                                             ('meta-charset', 'shift-jis')]

        with pytest.raises(UnicodeDecodeError):
            text = stream.read()
        assert stream.encoding == 'utf-8'

        stream.next_encoding()
        text = stream.read()
        assert stream.encoding == 'shift_jis'

        assert isinstance(text, text_type)
        assert text == '<meta charset="shift-jis">\n<p>巨<p>\n'


def test_htmlstream_meta_http_equiv():
    with stream_from_fixture('shift-jis-meta-http-equiv') as stream:
        assert stream.declared_encodings == [('http-content-type', 'ISO-8859-1'),
                                             ('meta-content-type', 'shift-jis')]

        with pytest.raises(UnicodeDecodeError):
            text = stream.read()
        assert stream.encoding == 'utf-8'

        stream.next_encoding()
        text = stream.read()
        assert stream.encoding == 'shift_jis'

        assert isinstance(text, text_type)
        assert text == '<meta http-equiv="content-type" content="text/html;charset=shift-jis">\n<p>巨<p>\n'  # flake8: noqa


def test_htmlstream_http_content_type():
    with stream_from_fixture('shift-jis-http-content-type') as stream:
        assert stream.declared_encodings == [('http-content-type', 'SHIFT-JIS'),
                                             ('meta-charset', 'iso-8859-1')]

        with pytest.raises(UnicodeDecodeError):
            text = stream.read()
        assert stream.encoding == 'utf-8'

        stream.next_encoding()
        text = stream.read()
        assert stream.encoding == 'shift_jis'
        assert text == '<meta charset="iso-8859-1">\n<p>巨<p>\n'


def test_htmlstream_next_encoding():
    with stream_from_fixture('shift-jis-next-decoder') as stream:
        assert stream.declared_encodings == [('http-content-type', 'SHIFT-JIS'),
                                             ('meta-charset', 'utf-8')]
        # HTMLStream likes the look of utf-8 in the <meta> charset
        # but the response is actually encoded in shift-jis so
        # this will raise a UnicodeDecodeError
        with pytest.raises(UnicodeDecodeError):
            stream.read()
        assert stream.encoding == 'utf-8'
        # now try the next encoding (shift-jis)
        stream.next_encoding()
        text = stream.read()
        assert stream.encoding == 'shift_jis'
        assert isinstance(text, text_type)
        assert text == '<meta charset="utf-8">\n<p>巨<p>\n'


def test_htmlstream_default_encoding():
    with stream_from_fixture('default') as stream:
        assert stream.declared_encodings == []
        # first default we try is utf-8
        with pytest.raises(UnicodeDecodeError):
            stream.read()
        # finally we try cp1252 with errors='replace'
        stream.next_encoding()
        text = stream.read()
        assert isinstance(text, text_type)
        assert text == '<p>�®</p>\n'
