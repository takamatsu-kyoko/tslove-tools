'''T's LOVEの日記を一括してダウンロードするプログラム'''

import argparse
import datetime
import getpass
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional, TypedDict

from bs4 import BeautifulSoup  # type: ignore
from PIL import Image  # type: ignore

from tslove.core.web import TsLoveWeb
from tslove.core.page import Page
from tslove.core.diary import DiaryPage
from tslove.core.exception import WebAccessError

DIARY_ID_PATTERN = re.compile(r'\./\?m=pc&a=page_fh_diary&target_c_diary_id=(?P<id>[0-9]+)')
URL_PATTERN = re.compile(r'url\((?P<path>.+)\)')

INTERVAL_SHORT = 10
INTERVAL_LONG = 20
INTERVAL_CHANGE_TIMING = 5


class OutputPath(TypedDict):
    '''ダンプの出力先'''
    base: str
    stylesheet: str
    image: str
    script: str
    tools: str


@dataclass
class Config:
    '''コンフィグ'''
    diary_id_from: str
    diary_id_to: str
    output_path: OutputPath
    echo_password: bool
    show_session_id: bool
    php_session_id: Optional[str] = None


def main():
    '''エントリポイント'''

    config = setup_config()

    web = TsLoveWeb(url='https://tslove.net/')
    if not login(web, config):
        print('Login failed.')
        sys.exit(1)

    if config.show_session_id:
        print(web.php_session_id)

    try:
        prepare_directories(config)
        dump_stylesheet(web, config)
        diary_id = check_first_diary_id(config)
        page_info = load_page_info(config)
    except (WebAccessError, OSError):
        sys.exit(1)

    first_download = True
    no_retry_count = 0
    interval = INTERVAL_LONG
    use_page_info = 0

    while diary_id:
        try:  # KeyBoardinterrupt

            file_name = os.path.join(config.output_path['base'], '{}.html'.format(diary_id))
            if os.path.exists(file_name):
                if diary_id not in page_info:
                    source = 'local'
                    try:
                        with open(file_name, 'r') as file:
                            diary_page = DiaryPage.read_from_file(file)
                    except OSError as err:
                        print('Processing diary id {} failed. (local) {}'.format(diary_id, err))
                        sys.exit(1)
                else:
                    source = 'page_info'
                    use_page_info += 1

                    if diary_id == config.diary_id_to or page_info[diary_id]['prev_diary_id'] is None:
                        break

                    diary_id = page_info[diary_id]['prev_diary_id']
                    continue

            else:
                source = 'remote'
                try:
                    if not first_download:
                        time.sleep(interval)
                    else:
                        first_download = False

                    retry_count = web.total_retries

                    diary_page = dump_diary(web, config, diary_id, file_name)

                    if web.total_retries == retry_count:
                        no_retry_count += 1
                    else:
                        no_retry_count = 0

                    if no_retry_count > INTERVAL_CHANGE_TIMING and interval != INTERVAL_SHORT:
                        print('interval changes {} sec. to {} sec.'.format(interval, INTERVAL_SHORT))
                        interval = INTERVAL_SHORT
                    if no_retry_count <= INTERVAL_CHANGE_TIMING and interval != INTERVAL_LONG:
                        print('interval changes {} sec. to {} sec.'.format(interval, INTERVAL_LONG))
                        interval = INTERVAL_LONG

                except (WebAccessError, OSError) as err:
                    print('Processing diary id {} failed. {}'.format(diary_id, err))
                    sys.exit(1)

            contents = {
                'title': diary_page.title,
                'date': diary_page.date,
                'prev_diary_id': diary_page.prev_diary_id,
                'diary_id': diary_id
            }

            page_info[diary_id] = contents

            print('diary id {} ({}:{}) processed.{}'.format(diary_id,
                                                            contents['date'].strftime('%Y-%m-%d'),
                                                            contents['title'],
                                                            '' if source == 'remote' else ' (local)'))

            if diary_id == config.diary_id_to or contents['prev_diary_id'] is None:
                break

            diary_id = contents['prev_diary_id']

        except KeyboardInterrupt:
            break

    try:
        save_page_info(config, page_info)
    except OSError:
        pass

    try:
        output_index(page_info, output_path=config.output_path['base'])
    except OSError as err:
        print('Can not save index file. {}'.format(err))
        sys.exit(1)

    if use_page_info:
        print('done. (skip {} diaries)'.format(use_page_info))
    else:
        print('done.')


def setup_config():
    '''コンフィグを生成します'''
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--from', help='diary_id to start', metavar='<id>', type=int, default=None)
    parser.add_argument('-t', '--to', help='diary_id to end', metavar='<id>', type=int, default=None)
    parser.add_argument('-o', '--output', help='destination to dump. (default ./dump)', metavar='<PATH>', default='./dump')
    parser.add_argument('--echo-password', help='display password on screen(DANGER)', action='store_true')
    parser.add_argument('--show-session-id', help='for debug', action='store_true')
    args = parser.parse_args()

    diary_id_from, diary_id_to = vars(args)['from'], args.to  # from is keyword
    if diary_id_from and diary_id_to and diary_id_from < diary_id_to:
        diary_id_from, diary_id_to = diary_id_to, diary_id_from

    base = os.path.join(args.output)
    config = Config(
        echo_password=args.echo_password,
        show_session_id=args.show_session_id,
        diary_id_from=str(diary_id_from) if diary_id_from else None,
        diary_id_to=str(diary_id_to) if diary_id_to else None,
        output_path={
            'base': base,
            'stylesheet': os.path.join(base, 'stylesheet'),
            'image': os.path.join(base, 'images'),
            'script': os.path.join(base, 'scripts'),
            'tools': os.path.join(base, 'tslove-tools')
        }
    )
    return config


def login(web, config):
    '''ログイン処理を行います'''
    try:
        if config.php_session_id is not None:
            if web.login(None, None, config.php_session_id):
                return True

        print('Enter username and password')
        username = input('user: ')
        if not config.echo_password:
            password = getpass.getpass(prompt='pass: ')
        else:
            password = input('pass: ')
        return web.login(username, password)
    except WebAccessError as err:
        print(err)
        return False


def prepare_directories(config):
    '''出力先のディレクトリを用意します'''
    directories = config.output_path.values()
    try:
        for directory in directories:
            if not os.path.exists(directory):
                os.mkdir(directory)
    except OSError as err:
        print('Can not create directory. {}'.format(err))
        raise err


def check_first_diary_id(config):
    '''最初にダウンロードする日記を取得します'''
    if config.diary_id_from is None:
        try:
            profile_page = BeautifulSoup(Page.fetch_from_web('page_h_prof').get_html_page(0), 'html.parser')
            diary_list = profile_page.find('ul', class_='articleList')
            result = DIARY_ID_PATTERN.match(diary_list.a['href'])
            return result.group('id')
        except WebAccessError as err:
            print('Can not get first diary id. {}'.format(err))
            raise err
    return config.diary_id_from


def dump_stylesheet(web, config):
    '''スタイルシートをダンプします'''
    stylesheet_file_name = os.path.join(config.output_path['stylesheet'], 'tslove.css')
    if not os.path.exists(stylesheet_file_name):
        try:
            stylesheet = web.get_stylesheet()
            image_paths = collect_stylesheet_image_paths(stylesheet)
            fetch_stylesheet_images(web, image_paths, output_path=config.output_path['stylesheet'])
            output_stylesheet(stylesheet, stylesheet_file_name)
        except (WebAccessError, OSError) as err:
            print('Can not get stylesheet. {}'.format(err))
            raise err


def collect_stylesheet_image_paths(stylesheet):
    '''スタイルシートに含まれる画像ファイルのパスを収集します'''
    paths = set()
    for line in stylesheet.splitlines():
        result = URL_PATTERN.search(line)
        if result:
            paths.add(result.group('path'))

    return paths


def fetch_stylesheet_images(web, image_paths, output_path='.', overwrite=False):
    '''スタイルシートに含まれる画像を取得します'''
    exclude_path = ['./skin/default/img/marker.gif']

    for path in image_paths:
        if path in exclude_path:
            continue

        filename = os.path.join(output_path, convert_stylesheet_image_path_to_filename(path))
        if os.path.exists(filename) and overwrite is False:
            continue

        try:
            image = web.get_image(path)
            image.save(filename)
        except (WebAccessError, OSError) as err:
            print('Can not get stylesheets image {}. {}'.format(path, err))
            continue


def convert_stylesheet_image_path_to_filename(path):
    '''スタイルシートに含まれる画像のパスをファイル名に変換します'''
    pattern = re.compile(r'image_filename=(?P<filename>[^&;?]+)')
    result = pattern.search(path)
    if result:
        filename = result.group('filename')
    else:
        filename = os.path.basename(path)

    return filename


def output_stylesheet(stylesheet, file_name):
    '''スタイルシートをファイルに出力します'''
    with open(file_name, 'w', encoding='utf-8') as file:
        for line in stylesheet.splitlines():
            result = URL_PATTERN.search(line)
            if result:
                old_path = result.group('path')
                new_path = './' + convert_stylesheet_image_path_to_filename(old_path)
                line = line.replace(old_path, new_path)
            file.write(line + '\n')


def dump_diary(web, config, diary_id, file_name):
    '''日記をダンプします'''
    diary_page = DiaryPage.fetch_from_web(diary_id)
    image_paths = diary_page.list_image_path()
    fetch_images(web, image_paths, output_path=config.output_path['image'])

    script_paths = diary_page.list_script_path()
    fetch_scripts(web, script_paths, output_path=config.output_path['script'])

    remove_script(diary_page.soup0)
    remove_form_items(diary_page.soup0)
    fix_link(diary_page.soup0, output_path=config.output_path['base'])

    with open(file_name, 'w', encoding='utf-8') as file:
        diary_page.write_to_file(file)

    return diary_page


def fetch_images(web, image_paths, output_path='.', overwrite=False):
    '''画像を取得します'''
    for path in image_paths:
        if '://' in path:
            continue

        filename = os.path.join(output_path, convert_image_path_to_filename(path))
        if os.path.exists(filename) and overwrite is False:
            continue

        try:
            if 'img.php' in path:
                params = {'m': 'pc',
                          'filename': convert_image_path_to_filename(path),
                          }
                image = web.get_image('img.php', params)
            else:
                image = web.get_image(path)
            image.save(filename)
        except (WebAccessError, OSError) as err:
            print('Can not get image {}. {}'.format(path, err))
            continue


def convert_image_path_to_filename(path):
    '''画像のパスをファイル名に変換します'''
    pattern = re.compile(r'filename=(?P<filename>[^&;?]+)')
    result = pattern.search(path)
    if result:
        filename = result.group('filename')
    else:
        filename = os.path.basename(path)

    return filename


def fetch_scripts(web, script_paths, output_path='.', overwrite=False):
    '''スクリプトを取得します'''
    for path in script_paths:

        if path.startswith('./js/prototype.js') or path.startswith('./js/Selection.js') or path == './js/comment.js':
            continue

        filename = os.path.join(output_path, convert_script_path_to_filename(path))
        if os.path.exists(filename) and overwrite is False:
            continue

        try:
            script = web.get_javascript(path)
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(script)

        except (WebAccessError, OSError) as err:
            print('Can not get script {}. {}'.format(path, err))
            continue


def convert_script_path_to_filename(path):
    '''スクリプトのパスをファイル名に変換します'''
    return os.path.basename(path)


def remove_script(soup):
    '''ページからスクリプトを除去します'''
    script_tags = soup.find_all('script')
    for script_tag in script_tags:
        if script_tag.has_attr('src'):
            src = script_tag['src']
            if src.startswith('./js/prototype.js') or src.startswith('./js/Selection.js') or src == './js/comment.js':
                script_tag.decompose()
        else:
            if 'url2cmd' not in script_tag.string:
                script_tag.decompose()

    a_tags_with_script = soup.find_all('a', onclick=True)
    for a_tag in a_tags_with_script:
        a_tag.decompose()


def remove_form_items(soup):
    '''ページからフォームアイテムを除去します'''
    div_tag = soup.find('div', id='commentForm')
    if div_tag:
        div_tag.decompose()

    div_tags = soup.find_all('div', class_='operation')
    for div_tag in div_tags:
        div_tag.decompose()

    form_tag = soup.find('form')
    if form_tag:
        form_tag.unwrap()

    input_tags = soup.find_all('input')
    for input_tag in input_tags:
        input_tag.decompose()


def fix_link(soup, output_path='.'):
    '''ページのリンクを修正します'''
    link_tag = soup.find('link', rel='stylesheet')
    if link_tag:
        link_tag['href'] = './stylesheet/tslove.css'

    a_tags_to_diary_list = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=page_fh_diary_list.*'))
    for a_tag_to_diary_list in a_tags_to_diary_list:
        a_tag_to_diary_list['href'] = './index.html'
        del a_tag_to_diary_list['rel']
        del a_tag_to_diary_list['target']

    a_tags_to_dialy = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=page_fh_diary.*'))
    for a_tag_to_dialy in a_tags_to_dialy:
        result = DIARY_ID_PATTERN.match(a_tag_to_dialy['href'])
        if result:
            diary_id = result.group('id')
            a_tag_to_dialy['href'] = './{}.html'.format(diary_id)
        else:
            a_tag_to_dialy['href'] = '#'
        del a_tag_to_dialy['rel']
        del a_tag_to_dialy['target']

    a_tags_to_top = soup.find_all('a', href='./')
    for a_tag_to_top in a_tags_to_top:
        a_tag_to_top['href'] = './index.html'
        del a_tag_to_top['rel']
        del a_tag_to_top['target']

    a_tags_to_action = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=.+'))
    for a_tag_to_action in a_tags_to_action:
        a_tag_to_action['href'] = '#'
        del a_tag_to_action['rel']
        del a_tag_to_action['target']

    a_tags_to_img = soup.find_all('a', href=re.compile(r'^(\./)?img.php.+'))
    for a_tag_to_img in a_tags_to_img:
        a_tag_to_img['href'] = './images/' + convert_image_path_to_filename(a_tag_to_img['href'])

    img_tags = soup.find_all('img')
    for img_tag in img_tags:
        path = os.path.join('./images/', convert_image_path_to_filename(img_tag['src']))
        if 'w=120&h=120' in img_tag['src']:
            target_file = os.path.join(output_path, path)

            if os.path.exists(target_file):
                image = Image.open(target_file)
                if image.size[0] == image.size[1]:
                    img_tag['width'] = 120
                    img_tag['height'] = 120
                elif image.size[0] > image.size[1]:
                    img_tag['width'] = 120
                else:
                    img_tag['height'] = 120
            else:
                img_tag['width'] = 120
                img_tag['height'] = 120
        img_tag['src'] = path

    for script_tag in soup.find_all('script', src=True):
        script_tag['src'] = 'scripts/' + convert_script_path_to_filename(script_tag['src'])


def load_page_info(config):
    '''ページ情報ファイルを読み込みます。'''
    def convert_datetime(dct):
        if 'date' in dct:
            dct['date'] = datetime.datetime.strptime(dct['date'], '%Y-%m-%d %H:%M:%S')
        return dct

    page_info_path = os.path.join(config.output_path['tools'], 'page_info.json')
    if os.path.exists(page_info_path):
        try:
            with open(page_info_path, 'r', encoding='utf-8') as file:
                return json.load(file, object_hook=convert_datetime)
        except OSError as err:
            print('Can not load page info {}. {}'.format(page_info_path, err))
            raise err
    else:
        return {}


def save_page_info(config, page_info):
    '''ページ情報ファイルを保存します'''
    page_info_path = os.path.join(config.output_path['tools'], 'page_info.json')

    try:
        with open(page_info_path, 'w', encoding='utf-8') as file:
            json.dump(page_info, file, ensure_ascii=False, indent=2, default=str)
    except OSError as err:
        print('Can not save page info {}. {}'.format(page_info_path, err))
        raise err


def output_index(page_info, output_path='.'):
    '''インデックスファイルを出力します'''
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
    <title>Index of dialy</title>
    <meta charset="utf-8"/>
    </head>
    <body>
    <h1>Index of dialy</h1>
    <table>
    <tr><th>Date</th><th>Title</th></tr>
    </table>
    </body>
    </html>
    '''

    soup = BeautifulSoup(template, 'html.parser')
    table_tag = soup.table

    for diary_id in sorted(page_info.keys(), reverse=True):
        tr_tag = soup.new_tag('tr')
        date_td_tag = soup.new_tag('td')
        date_td_tag.string = page_info[diary_id]['date'].strftime('%Y年%m月%d日%H:%M')
        tr_tag.append(date_td_tag)
        title_td_tag = soup.new_tag('td')
        title_a_tag = soup.new_tag('a')
        title_a_tag['href'] = './{}.html'.format(page_info[diary_id]['diary_id'])
        title_a_tag.string = page_info[diary_id]['title']
        title_td_tag.append(title_a_tag)
        tr_tag.append(title_td_tag)
        table_tag.append(tr_tag)

    file_name = os.path.join(output_path, 'index.html')
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(soup.prettify(formatter=None))


if __name__ == "__main__":
    main()
