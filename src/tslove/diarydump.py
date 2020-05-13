from bs4 import BeautifulSoup
import getpass
import re
import os
import time

import tslove.web

DIARY_ID_PATTERN = re.compile(r'\./\?m=pc&a=page_fh_diary&target_c_diary_id=(?P<id>[0-9]+)')
URL_PATTERN = re.compile(r'url\((?P<path>.+)\)')


def main():
    web = tslove.web.WebUI()
    php_session_id = None
    diary_id = None

    login = False
    try:
        if php_session_id is not None:
            login = web.login(None, None, php_session_id)

        if login is False:
            print('Enter username and password')
            username = input('user: ')
            password = getpass.getpass(prompt='pass: ')
            login = web.login(username, password)
    except Exception as e:
        print('Login failed. {}'.format(e))
        exit(1)

    if login is False:
        print('Login failed.')
        exit(1)

    try:
        stylesheet = web.get_stylesheet()
        image_paths = collect_stylesheet_image_paths(stylesheet)
        fetch_stylesheet_images(web, image_paths, output_path='./stylesheet')
        output_stylesheet(stylesheet, output_path='./stylesheet')
    except Exception as e:
        print('Can not get stylesheet. {}'.format(e))
        exit(1)

    if diary_id is None:
        try:
            profile_page = BeautifulSoup(web.get_myprofile_page(), 'html.parser')
            diary_list = profile_page.find('ul', class_='articleList')
            result = DIARY_ID_PATTERN.match(diary_list.a['href'])
            diary_id = result.group('id')
        except Exception as e:
            print('Can not get first diary id. {}'.format(e))
            exit(1)

    contents = None
    while diary_id:
        if contents:
            time.sleep(5)
        try:
            diary_page = BeautifulSoup(web.get_diary_page(diary_id), 'html.parser')
            contents = collect_contents(diary_page)
            output_diary(diary_id, contents, diary_page)
        except Exception as e:
            print('Processing diary id {} failed. {}'.format(diary_id, e))
            exit(1)

        print('diary id {} processed.'.format(diary_id))
        diary_id = contents['prev_diary_id']

    print('done.')


def collect_contents(soup):
    contents = {}
    contents['title'] = soup.find('p', class_='heading').string
    contents['date'] = soup.find('div', class_='dparts diaryDetailBox').div.dl.dt.get_text()

    result = soup.find('p', class_='prev')
    if result:
        result = DIARY_ID_PATTERN.match(result.a['href'])

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
    pattern = re.compile(r'image_filename=(?P<filename>.+)&*')
    result = pattern.search(path)
    if result:
        filename = result.group('filename')
    else:
        filename = os.path.basename(path)

    return filename


def output_stylesheet(stylesheet, output_path='.'):
    file_name = os.path.join(output_path, 'tslove.css')
    with open(file_name, 'w') as f:
        for line in stylesheet.splitlines():
            result = URL_PATTERN.search(line)
            if result:
                old_path = result.group('path')
                new_path = './' + convert_stylesheet_image_path_to_filename(old_path)
                line = line.replace(old_path, new_path)
            f.write(line + '\n')


def output_diary(diary_id, contents, soup, output_path='.'):
    print('date: {} title: {}'.format(contents['date'], contents['title']))

    file_name = os.path.join(output_path, '{}.html'.format(diary_id))
    with open(file_name, 'w') as f:
        f.write(soup.prettify(formatter=None))


if __name__ == "__main__":
    main()
