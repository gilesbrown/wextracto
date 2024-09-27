from io import FileIO
from six import next
import pytest
from wex.readable import EXT_WEXIN
from wex.output import EXT_WEXOUT
from wex import pytestplugin

@pytest.fixture
def parent(request):
    return request.session

response = b"""HTTP/1.1 200 OK\r
Content-type: application/json\r
\r
{"args":{"this":"that"}}"""


def test_pytest_collect_file(testme, tmpdir, parent):
    assert testme  # silence linter
    # FTM just to see how to coverage test the plugin
    r0_wexin = tmpdir.join('0' + EXT_WEXIN)
    r0_wexout = tmpdir.join('0' + EXT_WEXOUT)
    with FileIO(r0_wexin.strpath, 'w') as fp:
        fp.write(response)
    with FileIO(r0_wexout.strpath, 'w') as fp:
        fp.write(b'this\t"that"\n')
    fileobj = pytestplugin.pytest_collect_file(parent, r0_wexin)
    item = next(fileobj.collect())
    item.runtest()
