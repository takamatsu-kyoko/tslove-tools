imechen.py (イメチェン.py)
==========================

T's LOVEのプロフィール画像を差し替えます

## Description

T's LOVE(<https://tslove.net>)のプロフィール画像を差し替えます。
差し替える画像ファイルは予め指定しておいて、その中から一枚がランダムに選択されます。

## Features

- 差し替える画像ファイルはコンフィグファイル(config.ini)で指定します
    - 予めプロフィール画像として利用できるものを指定してください
- すでに3枚の画像が登録されている場合、3番目の画像を削除します
    - バックアップは取得されないのでご注意ください
- セッション情報をコンフィグファイルに保存し、次回以降使用します
    - セッション情報が無効になった場合はコンフィグファイルから削除してやり直してください。(config.iniから phpsessid = から始まる行を削除します)

## Requirement

python3系とrequestsモジュールが必要です。

## Usage

1. 画像ファイルを用意します
2. 設定ファイルを作成します
    - imechen.pyと同じディレクトリに config.ini として設置します
    - 内容については、config.ini.sampleを参照してください
    - パスワード等が含まれるのでパーミッションを確認してください
3. imechen.pyを実行します
    - 必要に応じて shebang (#! から始まる1行目) を変更してください

## Licence

[MIT](https://github.com/takamatsu-kyoko/tslove-tools/blob/master/LICENSE)

## Author

[高松 響子](https://github.com/takamatsu-kyoko/)
