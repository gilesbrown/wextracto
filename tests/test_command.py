from __future__ import unicode_literals, print_function
import os
import io
import errno
import sys
import time
import subprocess
from contextlib import contextmanager
from itertools import tee
from six import BytesIO
from six.moves import zip
from pathlib import Path
import pytest
from wex.readable import EXT_WEXIN
from wex.output import EXT_WEXOUT, TeeStdOut
from wex.url import URL
from wex import command


url = URL('http://httpbin.org/get?this=that')


here = Path(__file__).parent



def local_resource_filename(resource):
    return str(here.joinpath(resource))


@contextmanager
def local_resource_stream(resource):
    ref = here.joinpath(resource)
    with ref.open('rb') as fp:
        yield fp


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def find_file_paths(top):
    paths = []
    for dirpath, dirs, filenames in os.walk(top):
        paths.extend(os.path.join(dirpath, filename) for filename in filenames)
    return set(paths)


def start_wex_subprocess(args=['--help']):
    env = dict(os.environ)
    egg = str(here.joinpath('fixtures/TestMe.egg'))
    env['PYTHONPATH'] = egg
    # This test will fail unless you run setup.py develop or setup.py install
    exe = os.path.join(os.path.dirname(sys.executable), 'wex')
    cmd = [exe] + args
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env)


def test_wex_console_script(testme):
    # this url is cunningly crafted to generate UTF-8 output
    url = 'http://httpbin.org/get?this=that%C2%AE'
    wex = start_wex_subprocess([url])
    output = wex.stdout.read()
    assert wex.wait() == 0
    assert output == b'"this"\t"that\xc2\xae"\n'


def test_wex_multiprocessing():
    url = 'http://httpbin.org/get?this=that%C2%AE'
    wex = start_wex_subprocess(['-P', url])
    ret = None
    for i in range(300):
        ret = wex.poll()
        if ret is None:
            time.sleep(0.1)
    assert ret is not None


def run_main(monkeypatch, args):
    argv = sys.argv[:1] + list(args)
    monkeypatch.setattr(sys, 'argv', argv)
    stdout = io.StringIO()
    monkeypatch.setattr('wex.output.StdOut.stdout', stdout)
    command.main()
    return stdout.getvalue()


def test_main_url(testme, monkeypatch):
    assert run_main(monkeypatch, [url]) == '"this"\t"that"\n'


def test_main_tarfile(testme, monkeypatch):
    example_tar = local_resource_filename('fixtures/example.tar')
    assert run_main(monkeypatch, [example_tar]) == '"this"\t"that"\n'


def test_main_save(testme, monkeypatch, tmpdir):
    destdir = tmpdir.strpath
    args = ['--save-dir', destdir, url]
    assert run_main(monkeypatch, args) == '"this"\t"that"\n'

    sentinel = object()
    expected_dirs = [
        'http',
        'httpbin.org',
        'get',
        'this%3Dthat',
        '178302e981e586827bd8ca962c1c27f8',
        sentinel
    ]
    dirpath = destdir
    for dirname, subdir in pairwise(expected_dirs):
        dirpath = os.path.join(dirpath, dirname)
        if subdir is not sentinel:
            assert os.listdir(dirpath) == [subdir]
    assert sorted(os.listdir(dirpath)) == ['0.wexin', '0.wexout']


def test_main_no_such_file(monkeypatch):
    argv = sys.argv[:1] + ['no-such-file']
    monkeypatch.setattr(sys, 'argv', argv)
    with pytest.raises(SystemExit) as excinfo:
        command.main()
    assert isinstance(excinfo.value.args[0], IOError)
    assert excinfo.value.args[0].errno == errno.ENOENT


def test_main_output_return_list(testme, monkeypatch, tmpdir):
    empty = local_resource_filename('fixtures/empty.wexin_')
    args = [empty]
    monkeypatch.chdir(tmpdir)
    with tmpdir.join('entry_points.txt').open('w') as fp:
        fp.write("[wex]\nreturn_list = testme:return_list")
    assert run_main(monkeypatch, args) == '[1,2]\n'


def test_main_output_return_tuple(testme, monkeypatch, tmpdir):
    empty = local_resource_filename('fixtures/empty.wexin_')
    args = [empty]
    monkeypatch.chdir(tmpdir)
    with tmpdir.join('entry_points.txt').open('w') as fp:
        fp.write("[wex]\nreturn_tuple = testme:return_tuple")
    # The tuple is encoded as a JSON array
    assert run_main(monkeypatch, args) == '[1,2]\n'


def test_main_output_return_dict(testme, monkeypatch, tmpdir):
    empty = local_resource_filename('fixtures/empty.wexin_')
    args = [empty]
    monkeypatch.chdir(tmpdir)
    with tmpdir.join('entry_points.txt').open('w') as fp:
        fp.write("[wex]\nreturn_dict = testme:return_dict")

    from wex.entrypoints import ExtractorFromEntryPoints


    # The tuple is encoded as a JSON array
    assert run_main(monkeypatch, args) == '{"a":1}\n'


wexin = b"""HTTP/1.1 200 OK

Hello
"""


def test_write_extracted_values_tee_stdout(tmpdir):
    readable = BytesIO(wexin)
    readable.name = tmpdir.join('0' + EXT_WEXIN).strpath
    def extract(src):
        yield 1
    writer = command.WriteExtractedValues(TeeStdOut, extract)
    ret = writer(readable)
    assert ret is None
    with tmpdir.join('0' + EXT_WEXOUT).open() as fp:
        assert fp.read() == '1\n'


def test_write_extracted_values_tee_stdout_readable_has_no_name():
    readable = BytesIO(wexin)
    def extract(src):
        yield 1
    writer = command.WriteExtractedValues(TeeStdOut, extract)
    ret = writer(readable)
    assert ret is None
