from bs4 import BeautifulSoup
from PIL import Image
import getpass
import argparse
import re
import os
import time
import datetime
import json

import tslove.web

DIARY_ID_PATTERN = re.compile(r'\./\?m=pc&a=page_fh_diary&target_c_diary_id=(?P<id>[0-9]+)')
FIXED_DIARY_ID_PATTERN = re.compile(r'\./(?P<id>[0-9]+).html')
URL_PATTERN = re.compile(r'url\((?P<path>.+)\)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--from', help='diary_id to start', metavar='<id>', type=int, default=None)
    parser.add_argument('-t', '--to', help='diary_id to end', metavar='<id>', type=int, default=None)
    parser.add_argument('-o', '--output', help='destination to dump. (default ./dump)', metavar='<PATH>', default='./dump')
    parser.add_argument('--echo-password', help='display password on screen(DANGER)', action='store_true')
    parser.add_argument('--php-session-id', metavar='', help='for debug', default=None)
    args = parser.parse_args()

    web = tslove.web.WebUI(url='https://tslove.net/')
    php_session_id = args.php_session_id

    diary_id_from, diary_id_to = vars(args)['from'], args.to  # from is keyword
    if diary_id_from and diary_id_to and diary_id_from < diary_id_to:
        diary_id_from, diary_id_to = diary_id_to, diary_id_from

    if diary_id_from:
        diary_id_from = str(diary_id_from)
    if diary_id_to:
        diary_id_to = str(diary_id_to)

    output_path = os.path.join(args.output)
    stylesheet_output_path = os.path.join(output_path, 'stylesheet')
    image_output_path = os.path.join(output_path, 'images')
    script_path = os.path.join(output_path, 'scripts')
    tools_path = os.path.join(output_path, 'tslove-tools')

    interval_short = 10
    interval_long = 20
    interval_change_timing = 5

    login = False
    try:
        if php_session_id is not None:
            login = web.login(None, None, php_session_id)

        if login is False:
            print('Enter username and password')
            username = input('user: ')
            if not args.echo_password:
                password = getpass.getpass(prompt='pass: ')
            else:
                password = input('pass: ')
            login = web.login(username, password)
    except Exception as e:
        print('Login failed. {}'.format(e))
        exit(1)

    if login is False:
        print('Login failed.')
        exit(1)

    directories = [output_path, stylesheet_output_path, image_output_path, script_path, tools_path]
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.mkdir(directory)
        except Exception as e:
            print('Can not create directory {}. {}'.format(directory, e))
            exit(1)

    stylesheet_file_name = os.path.join(stylesheet_output_path, 'tslove.css')
    if not os.path.exists(stylesheet_file_name):
        try:
            stylesheet = web.get_stylesheet()
            image_paths = collect_stylesheet_image_paths(stylesheet)
            fetch_stylesheet_images(web, image_paths, output_path=stylesheet_output_path)
            output_stylesheet(stylesheet, stylesheet_file_name)
        except Exception as e:
            print('Can not get stylesheet. {}'.format(e))
            exit(1)

    if diary_id_from is None:
        try:
            profile_page = BeautifulSoup(web.get_myprofile_page(), 'html.parser')
            diary_list = profile_page.find('ul', class_='articleList')
            result = DIARY_ID_PATTERN.match(diary_list.a['href'])
            diary_id = result.group('id')
        except Exception as e:
            print('Can not get first diary id. {}'.format(e))
            exit(1)
    else:
        diary_id = diary_id_from

    page_info = {}

    page_info_path = os.path.join(tools_path, 'page_info.json')
    if os.path.exists(page_info_path):
        try:
            page_info = load_page_info(page_info_path)
        except Exception as e:
            print('Can not load page info {}. {}'.format(page_info_path, e))
            exit(1)

    first_download = True
    no_retry_count = 0
    interval = interval_long
    use_page_info = 0

    while diary_id:
        try:  # KeyBoardinterrupt

            file_name = os.path.join(output_path, '{}.html'.format(diary_id))
            if os.path.exists(file_name):
                if diary_id not in page_info:
                    source = 'local'
                    try:
                        with open(file_name, 'r', encoding='utf-8') as f:
                            diary_page = BeautifulSoup(f, 'html.parser')
                    except Exception as e:
                        print('Processing diary id {} failed. (local) {}'.format(diary_id, e))
                        exit(1)
                else:
                    source = 'page_info'
                    use_page_info += 1

                    if diary_id == diary_id_to or page_info[diary_id]['prev_diary_id'] is None:
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

                    web.last_retries = 0

                    diary_page = BeautifulSoup(web.get_diary_page(diary_id), 'html.parser')
                    image_paths = collect_image_paths(diary_page)
                    fetch_images(web, image_paths, output_path=image_output_path)

                    script_paths = collect_script_paths(diary_page)
                    fetch_scripts(web, script_paths, output_path=script_path)

                    remove_script(diary_page)
                    remove_form_items(diary_page)
                    fix_link(diary_page, output_path=output_path)

                    output_diary(diary_page, file_name)

                    if web.last_retries == 0:
                        no_retry_count += 1
                    else:
                        no_retry_count = 0

                    if no_retry_count > interval_change_timing and not interval == interval_short:
                        print('interval changes {} sec. to {} sec.'.format(interval, interval_short))
                        interval = interval_short
                    if no_retry_count <= interval_change_timing and not interval == interval_long:
                        print('interval changes {} sec. to {} sec.'.format(interval, interval_long))
                        interval = interval_long

                except Exception as e:
                    print('Processing diary id {} failed. {}'.format(diary_id, e))
                    exit(1)

            contents = collect_contents(diary_page)
            contents['diary_id'] = diary_id

            page_info[diary_id] = contents

            print('diary id {} ({}:{}) processed.{}'.format(diary_id,
                                                            contents['date'].strftime('%Y-%m-%d'),
                                                            contents['title'],
                                                            '' if source == 'remote' else ' (local)'))

            if diary_id == diary_id_to or contents['prev_diary_id'] is None:
                break

            diary_id = contents['prev_diary_id']

        except KeyboardInterrupt:
            break

    try:
        save_page_info(page_info, page_info_path)
    except Exception as e:
        print('Can not save page info {}. {}'.format(page_info_path, e))

    try:
        output_index(page_info, output_path=output_path)
    except Exception as e:
        print('Can not save index file. {}'.format(e))
        exit(1)

    if use_page_info:
        print('done. (skip {} diaries)'.format(use_page_info))
    else:
        print('done.')


def collect_contents(soup):
    contents = {}
    contents['title'] = str(soup.find('p', class_='heading').get_text(strip=True))

    date = str(soup.find('div', class_='dparts diaryDetailBox').div.dl.dt.get_text(strip=True))
    contents['date'] = datetime.datetime.strptime(date, '%Y年%m月%d日%H:%M')

    result = soup.find('p', class_='prev')
    if result:
        result = FIXED_DIARY_ID_PATTERN.match(result.a['href'])

    if result:
        contents['prev_diary_id'] = result.group('id')
    else:
        contents['prev_diary_id'] = None

    return contents


def collect_stylesheet_image_paths(stylesheet):
    paths = set()
    for line in stylesheet.splitlines():
        result = URL_PATTERN.search(line)
        if result:
            paths.add(result.group('path'))

    return paths


def fetch_stylesheet_images(web, image_paths, output_path='.', overwrite=False):
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
        except Exception as e:
            print('Can not get stylesheets image {}. {}'.format(path, e))
            continue


def convert_stylesheet_image_path_to_filename(path):
    pattern = re.compile(r'image_filename=(?P<filename>[^&;?]+)')
    result = pattern.search(path)
    if result:
        filename = result.group('filename')
    else:
        filename = os.path.basename(path)

    return filename


def output_stylesheet(stylesheet, file_name):
    with open(file_name, 'w', encoding='utf-8') as f:
        for line in stylesheet.splitlines():
            result = URL_PATTERN.search(line)
            if result:
                old_path = result.group('path')
                new_path = './' + convert_stylesheet_image_path_to_filename(old_path)
                line = line.replace(old_path, new_path)
            f.write(line + '\n')


def collect_image_paths(soup):
    paths = set()
    for img_tag in soup.find_all('img'):
        if '://' not in img_tag['src']:
            paths.add(img_tag['src'])

    return paths


def fetch_images(web, image_paths, output_path='.', overwrite=False):

    for path in image_paths:
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
        except Exception as e:
            print('Can not get image {}. {}'.format(path, e))
            continue


def convert_image_path_to_filename(path):
    pattern = re.compile(r'filename=(?P<filename>[^&;?]+)')
    result = pattern.search(path)
    if result:
        filename = result.group('filename')
    else:
        filename = os.path.basename(path)

    return filename


def collect_script_paths(soup):
    paths = set()

    for script_tag in soup.find_all('script', src=True):
        src = script_tag['src']
        if not src.startswith('./js/prototype.js') and not src.startswith('./js/Selection.js') and not src == './js/comment.js':
            paths.add(script_tag['src'])

    return paths


def fetch_scripts(web, script_paths, output_path='.', overwrite=False):
    for path in script_paths:
        filename = os.path.join(output_path, convert_script_path_to_filename(path))
        if os.path.exists(filename) and overwrite is False:
            continue

        try:
            script = web.get_javascript(path)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(script)

        except Exception as e:
            print('Can not get script {}. {}'.format(path, e))
            continue


def convert_script_path_to_filename(path):
    return os.path.basename(path)


def remove_script(soup):
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
    link_tag = soup.find('link', rel='stylesheet')
    if link_tag:
        link_tag['href'] = './stylesheet/tslove.css'

    a_tags_to_diary_list = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=page_fh_diary_list.*'))
    for a_tag_to_diary_list in a_tags_to_diary_list:
        a_tag_to_diary_list['href'] = './index.html'
        del(a_tag_to_diary_list['rel'])
        del(a_tag_to_diary_list['target'])

    a_tags_to_dialy = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=page_fh_diary.*'))
    for a_tag_to_dialy in a_tags_to_dialy:
        result = DIARY_ID_PATTERN.match(a_tag_to_dialy['href'])
        if result:
            diary_id = result.group('id')
            a_tag_to_dialy['href'] = './{}.html'.format(diary_id)
        else:
            a_tag_to_dialy['href'] = '#'
        del(a_tag_to_dialy['rel'])
        del(a_tag_to_dialy['target'])

    a_tags_to_top = soup.find_all('a', href='./')
    for a_tag_to_top in a_tags_to_top:
        a_tag_to_top['href'] = './index.html'
        del(a_tag_to_top['rel'])
        del(a_tag_to_top['target'])

    a_tags_to_action = soup.find_all('a', href=re.compile(r'^(\./)?\?m=pc&a=.+'))
    for a_tag_to_action in a_tags_to_action:
        a_tag_to_action['href'] = '#'
        del(a_tag_to_action['rel'])
        del(a_tag_to_action['target'])

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


def output_diary(soup, file_name):
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(soup.prettify(formatter=None))


def load_page_info(file_name):
    def convert_datetime(dct):
        if 'date' in dct:
            dct['date'] = datetime.datetime.strptime(dct['date'], '%Y-%m-%d %H:%M:%S')
        return dct

    with open(file_name, 'r', encoding='utf-8') as f:
        return json.load(f, object_hook=convert_datetime)


def save_page_info(page_info, file_name):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(page_info, f, ensure_ascii=False, indent=2, default=str)


def output_index(page_info, output_path='.'):
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

    for diary_id in sorted(page_info.keys(), key=int, reverse=True):
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
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(soup.prettify(formatter=None))


if __name__ == "__main__":
    main()
