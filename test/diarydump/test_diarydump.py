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


@pytest.fixture(scope='module')
def stylesheet():
    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/original-stylesheet.css')
    with open(data_file, 'r') as f:
        stylesheet = f.read()
    return stylesheet


def test_collect_stylesheet_image_paths(stylesheet):
    expect_path = set([
        './img_skin.php?filename=skin_after_header&amp;image_filename=skin_skin_after_header_1173622663.gif',
        './img_skin.php?filename=skin_before_header&amp;image_filename=skin_skin_before_header_1173622709.gif',
        './img_skin.php?filename=skin_footer&amp;image_filename=skin_skin_footer_1206286337.gif',
        './img_skin.php?filename=skin_navi_c&amp;image_filename=skin_skin_navi_c_1153129448.gif',
        './img_skin.php?filename=skin_navi_f&amp;image_filename=skin_skin_navi_f_1153129442.gif',
        './img_skin.php?filename=skin_navi_h&amp;image_filename=skin_skin_navi_h_1153128989.gif',
        './skin/default/img/articleList_marker.gif',
        './skin/default/img/bg_button.gif',
        './skin/default/img/colon.gif',
        './skin/default/img/content_header_1.gif',
        './skin/default/img/icon_1.gif',
        './skin/default/img/icon_2.gif',
        './skin/default/img/icon_3.gif',
        './skin/default/img/icon_arrow_1.gif',
        './skin/default/img/icon_arrow_2.gif',
        './skin/default/img/icon_information.gif',
        './skin/default/img/icon_title_1.gif',
        './skin/default/img/marker.gif',
    ])

    assert expect_path == tslove.diarydump.collect_stylesheet_image_paths(stylesheet)


def test_convert_stylesheet_image_path_to_filename():
    filename = tslove.diarydump.convert_stylesheet_image_path_to_filename('./skin/default/img/icon_title_1.gif')
    assert 'icon_title_1.gif' == filename

    filename = tslove.diarydump.convert_stylesheet_image_path_to_filename('./img_skin.php?filename=skin_after_header&amp;image_filename=skin_skin_after_header_1173622663.gif')
    assert 'skin_skin_after_header_1173622663.gif' == filename


def test_output_stylesheet(stylesheet, tmpdir):
    tslove.diarydump.output_stylesheet(stylesheet, output_path=tmpdir)

    assert filecmp.cmp(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/expect-stylesheet.css'),
                       os.path.join(tmpdir, 'tslove.css'))


def test_output_htmlfile(diary_page, tmpdir):
    contents = {'title': 'dummy', 'date': 'dummy'}
    soup = BeautifulSoup(diary_page, 'html.parser')

    tslove.diarydump.remove_script(soup)
    tslove.diarydump.remove_form_items(soup)
    tslove.diarydump.fix_link(soup)

    tslove.diarydump.output_diary('actual-diary-page', contents, soup, output_path=tmpdir)

    assert filecmp.cmp(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/expect-diary-page.html'),
                       os.path.join(tmpdir, 'actual-diary-page.html'))
