import pytest
from bs4 import BeautifulSoup
import os
import shutil
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


@pytest.fixture()
def dummy_image_file(tmpdir):
    image_file1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/dummy_image1.jpg')
    image_file2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/dummy_image2.jpg')
    image_file3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/dummy_image3.jpg')

    image_dir = os.path.join(tmpdir, 'images')
    os.mkdir(image_dir)

    shutil.copy(image_file1, os.path.join(image_dir, 'd_2653068_1_1587025918.jpg'))
    shutil.copy(image_file2, os.path.join(image_dir, 'd_2653068_2_1587025918.jpg'))
    shutil.copy(image_file3, os.path.join(image_dir, 'd_2653068_3_1587025918.jpg'))


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


def test_collect_image_paths(diary_page):
    expect_path = set([
        './img.php?filename=b_47_1584929146.jpg&m=pc',
        './img.php?filename=d_2653068_1_1587025918.jpg&w=120&h=120&m=pc',
        './img.php?filename=d_2653068_2_1587025918.jpg&w=120&h=120&m=pc',
        './img.php?filename=d_2653068_3_1587025918.jpg&w=120&h=120&m=pc',
        './skin/default/img/button_comment.gif',
        '/img/ad/hige_pc.jpg',
        '/img/ad/Yamadaya_ad2005pc.gif',
        '/img/ad/ts_owl.gif',
        '/img/ad/josocafe-c2003.gif',
        '/img/ad/TLban_200227.jpg',
    ])

    soup = BeautifulSoup(diary_page, 'html.parser')
    assert expect_path == tslove.diarydump.collect_image_paths(soup)


def test_convert_image_path_to_filename():
    filename = tslove.diarydump.convert_image_path_to_filename('./skin/default/img/button_comment.gif')
    assert 'button_comment.gif' == filename

    filename = tslove.diarydump.convert_image_path_to_filename('./img.php?filename=d_2653068_3_1587025918.jpg&amp;w=120&amp;h=120&amp;m=pc')
    assert 'd_2653068_3_1587025918.jpg' == filename


def test_output_htmlfile(diary_page, dummy_image_file, tmpdir):
    contents = {'title': 'dummy', 'date': 'dummy'}
    soup = BeautifulSoup(diary_page, 'html.parser')

    tslove.diarydump.remove_script(soup)
    tslove.diarydump.remove_form_items(soup)
    tslove.diarydump.fix_link(soup, output_path=tmpdir)

    tslove.diarydump.output_diary('actual-diary-page', contents, soup, output_path=tmpdir)

    assert filecmp.cmp(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/expect-diary-page.html'),
                       os.path.join(tmpdir, 'actual-diary-page.html'))
