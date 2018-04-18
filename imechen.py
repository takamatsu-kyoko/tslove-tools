#! /usr/bin/env python3
"""
Ts'LOVE のプロフィール写真を差し替えます
"""

import requests
import re
import warnings
import glob
import random
import sys
import configparser
import os

warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made.')

TSLOVE_URL = 'https://tslove.net/'
CONFIG_FILE = os.path.join(sys.path[0], 'config.ini')

config = configparser.ConfigParser()
cookie = {}


def get_phpsessionid():
    """ T's LOVE にログインしてPHPSESSIONを返します

    取得したPHPSESSIONの値をコンフィグファイルに書き込みます
    PHPSESSIONが取得できなかった場合 None を返します
    """

    payload = {'username': config['DEFAULT']['UserName'],
               'password': config['DEFAULT']['Password'],
               'm': 'pc',
               'a': 'do_o_login',
               'login_params': '',
               'is_save': '1',
               }
    response = requests.post(TSLOVE_URL, data=payload, verify=False, allow_redirects=False)
    response.raise_for_status()

    if 'PHPSESSID' not in response.cookies:
        return None

    config['DEFAULT']['PHPSESSID'] = response.cookies['PHPSESSID']

    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

    return response.cookies['PHPSESSID']


def get_img_num_and_sessionid():
    """ 写真を編集するページを取得して写真の枚数とsessidを返します

    sessidが取得できなかった場合 None を返します
    """

    params = {'m': 'pc',
              'a': 'page_h_config_image'}

    response = requests.get(TSLOVE_URL, params=params, cookies=cookie, verify=False)
    response.raise_for_status()

    logout_link_pattern = re.compile(
        r'<a href="\./\?m=pc&amp;a=do_inc_page_header_logout&amp;sessid=(?P<sessid>[a-z0-9]+)">')

    sessid = None
    img_num = 0

    for line in response.text.splitlines():
        if not sessid:
            match = logout_link_pattern.search(line)
            if match:
                sessid = match.group('sessid')
                delete_link_pattern = re.compile(r'<a href="\./\?m=pc&amp;'
                                                 'a=do_h_config_image_delete_c_member_image&amp;'
                                                 'img_num=(?P<img_num>[123])&amp;sessid={}">'.format(sessid))
        if sessid:
            match = delete_link_pattern.search(line)
            if match:
                img_num = int(match.group('img_num'))

    return (img_num, sessid)


def get_new_file():
    """ 新しい画像ファイルのファイル名を返します

    ファイル名のglobはコンフィグファイルで指定します
    見つかったファイル名の中からランダムで一つ返します
    """

    files = glob.glob(config['imechen']['ImageFiles'])

    if len(files) == 0:
        return None

    random.seed()
    return random.choice(files)


def delete_image(img_num):
    """ プロフィール画像から指定されたスロットの写真を削除します

    削除したファイルのバックアップ等は作成しません
    """

    params = {'m': 'pc',
              'a': 'do_h_config_image_delete_c_member_image',
              'img_num': img_num,
              'sessid': config['DEFAULT']['sessid']}
    response = requests.get(TSLOVE_URL, params=params, cookies=cookie, verify=False)
    response.raise_for_status()


def upload_file(new_file_name):
    """ 指定されたファイルをアップロードします """

    payload = {'m': 'pc',
               'a': 'do_h_config_image',
               'MAX_FILE_SIZE': '307200',
               'sessid': config['DEFAULT']['sessid'], }

    with open(new_file_name, 'rb') as upload_file:
        response = requests.post(TSLOVE_URL, data=payload, cookies=cookie,
                                 files={'upfile': upload_file}, verify=False)
        response.raise_for_status()


def activate_image(img_num):
    """ 指定されたスロットの写真をメイン写真に設定します """

    params = {'m': 'pc',
              'a': 'do_h_config_image_change_main_c_member_image',
              'img_num': img_num,
              'sessid': config['DEFAULT']['sessid']}
    response = requests.get(TSLOVE_URL, params=params, cookies=cookie, verify=False)
    response.raise_for_status()


def main():
    """ エントリポイント """

    config.read(CONFIG_FILE)

    if 'PHPSESSID' not in config['DEFAULT']:
        phpsessid = get_phpsessionid()
        if not phpsessid:
            sys.stderr.write('PHPSESSIDの取得に失敗しました。\n')
            sys.exit(1)
    else:
        phpsessid = config['DEFAULT']['PHPSESSID']

    cookie['PHPSESSID'] = phpsessid

    (img_num, sessid) = get_img_num_and_sessionid()

    if not sessid:
        sys.stderr.write('sessidの取得に失敗しました。\n'
                         'PHPSESSIDが無効になっている場合は削除して再実行してください。\n')
        sys.exit(1)

    config['DEFAULT']['sessid'] = sessid

    new_file_name = get_new_file()
    if not new_file_name:
        sys.stderr.write('画像ファイルが見つかりませんでした。\n')
        sys.exit(1)

    if img_num == 3:
        delete_image(3)
        img_num -= 1

    upload_file(new_file_name)

    if img_num != 0:
        activate_image(img_num + 1)


if __name__ == "__main__":
    main()
