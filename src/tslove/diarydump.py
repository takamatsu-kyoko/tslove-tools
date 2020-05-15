from bs4 import BeautifulSoup
from PIL import Image
import getpass
import argparse
import re
import os
import time
import datetime

import tslove.web

DIARY_ID_PATTERN = re.compile(r'\./\?m=pc&a=page_fh_diary&target_c_diary_id=(?P<id>[0-9]+)')
URL_PATTERN = re.compile(r'url\((?P<path>.+)\)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--from', help='diary_id to start', metavar='<id>', type=int, default=None)
    parser.add_argument('-t', '--to', help='diary_id to end', metavar='<id>', type=int, default=None)
    parser.add_argument('-o', '--output', help='destination to dump. (default ./dump)', metavar='<PATH>', default='./dump')
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

    page_info = []

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

    directories = [output_path, stylesheet_output_path, image_output_path]
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.mkdir(directory)
        except Exception as e:
            print('Can not create directory {}. {}'.format(directory, e))
            exit(1)

    try:
        stylesheet = web.get_stylesheet()
        image_paths = collect_stylesheet_image_paths(stylesheet)
        fetch_stylesheet_images(web, image_paths, output_path=stylesheet_output_path)
        output_stylesheet(stylesheet, output_path=stylesheet_output_path)
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

    contents = None
    while diary_id:
        try:
            if contents:
                time.sleep(5)

            diary_page = BeautifulSoup(web.get_diary_page(diary_id), 'html.parser')
            contents = collect_contents(diary_page)
            contents['diary_id'] = diary_id

            image_paths = collect_image_paths(diary_page)
            fetch_images(web, image_paths, output_path=image_output_path)

            remove_script(diary_page)
            remove_form_items(diary_page)
            fix_link(diary_page, output_path=output_path)

            output_diary(diary_id, contents, diary_page, output_path=output_path)

            page_info.append(contents)
        except Exception as e:
            print('Processing diary id {} failed. {}'.format(diary_id, e))
            exit(1)
        except KeyboardInterrupt:
            break

        print('diary id {} ({}) processed.'.format(diary_id, contents['title']))

        if diary_id == diary_id_to:
            break

        diary_id = contents['prev_diary_id']

    output_index(page_info, output_path=output_path)
    print('done.')


def collect_contents(soup):
    contents = {}
    contents['title'] = str(soup.find('p', class_='heading').string)

    date = str(soup.find('div', class_='dparts diaryDetailBox').div.dl.dt.get_text())
    contents['date'] = datetime.datetime.strptime(date, '%Y年%m月%d日%H:%M')

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
    pattern = re.compile(r'image_filename=(?P<filename>[^&;?]+)')
    result = pattern.search(path)
    if result:
        filename = result.group('filename')
    else:
        filename = os.path.basename(path)

    return filename


def output_stylesheet(stylesheet, output_path='.'):
    file_name = os.path.join(output_path, 'tslove.css')
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


def remove_script(soup):
    script_tags = soup.find_all('script')
    for script_tag in script_tags:
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
        path = './images/' + convert_image_path_to_filename(img_tag['src'])
        if 'w=120&h=120' in img_tag['src']:
            image = Image.open(os.path.join(output_path, path))
            if image.size[0] == image.size[1]:
                img_tag['width'] = 120
                img_tag['height'] = 120
            elif image.size[0] > image.size[1]:
                img_tag['width'] = 120
            else:
                img_tag['height'] = 120
        img_tag['src'] = path


def output_diary(diary_id, contents, soup, output_path='.'):
    file_name = os.path.join(output_path, '{}.html'.format(diary_id))
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(soup.prettify(formatter=None))


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

    for info in page_info:
        tr_tag = soup.new_tag('tr')
        date_td_tag = soup.new_tag('td')
        date_td_tag.string = info['date'].strftime('%Y年%m月%d日%H:%M')
        tr_tag.append(date_td_tag)
        title_td_tag = soup.new_tag('td')
        title_a_tag = soup.new_tag('a')
        title_a_tag['href'] = './{}.html'.format(info['diary_id'])
        title_a_tag.string = info['title']
        title_td_tag.append(title_a_tag)
        tr_tag.append(title_td_tag)
        table_tag.append(tr_tag)

    file_name = os.path.join(output_path, 'index.html')
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(soup.prettify(formatter=None))


if __name__ == "__main__":
    main()
