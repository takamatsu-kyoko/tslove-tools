import pytest
from bs4 import BeautifulSoup
import os
import filecmp

import tslove.diarydump


@pytest.fixture(scope='module')
def diary_page():
    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/original-diary-page.html')
    with open(data_file, 'r') as f:
        html = f.read()
    return html


def test_output_htmlfile(diary_page, tmpdir):
    contents = {'title': 'dummy', 'date': 'dummy'}
    soup = BeautifulSoup(diary_page, 'html.parser')

    tslove.diarydump.output_diary('actual-diary-page', contents, soup, output_path=tmpdir)

    print(os.path.join(tmpdir, 'actual-diary-page.html'))
    print(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/expect-diary-page.html'))

    assert filecmp.cmp(os.path.join(tmpdir, 'actual-diary-page.html'),
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/expect-diary-page.html'))
