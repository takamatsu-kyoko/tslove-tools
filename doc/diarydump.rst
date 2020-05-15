diarydump
=========

T's LOVEの日記を一括してダウンロードします

Description
-----------

T's LOVEの日記を一括してダウンロードします。
スタイルシートや画像ファイルも合わせてダウンロードするので、実サイトの見栄えをある程度維持したまま日記を保存することができます。

Fratures
--------

- 何も指定しなければログインしたユーザのすべての日記を取得します
- 取得する日記の範囲をdiary_idの値で指定することができます

  - diary_idは日記ページのURLのtarget_c_diary_id= に続く番号です

- スタイルシートと画像ファイルも取得してリンクを調整します
- 取得した日記の一覧ページ(index.htmlファイル)を作成します

Usage
-----

何も指定せずに diarydump コマンドを実行するとログインしたユーザのすべての日記を dump フォルダにダウンロードします。
コマンド実行をするとまず最初に T's LOVE のユーザ名(メールアドレス)とパスワードを聞いてくるので入力してください。
dump フォルダーはコマンドを実行した場所に作成されます。

ダウンロード先や取得する日記の範囲はコマンドラインから指定できます。

::

  usage: diarydump [-h] [-f <id>] [-t <id>] [-o <PATH>] [--php-session-id]
  
  optional arguments:
    -h, --help            show this help message and exit
    -f <id>, --from <id>  diary_id to start
    -t <id>, --to <id>    diary_id to end
    -o <PATH>, --output <PATH>
                          destination to dump. (default ./dump)
    --php-session-id      for debug

何も指定せずに実行した場合は以下のような画面になります。dumpフォルダにすべての日記がダウンロードされます。

::

  diarydump
  Enter username and password
  user: <ここでユーザ名を入力します>
  pass: <ここでパスワードを入力します>
  diary id 2664309 (日記をバックアップするプログラム) processed.  
  diary id 2653068 (普段着) processed.
  diary id 2651906 (化粧品の代謝) processed.
    : (中略)
  diary id 1485356 (お気に入り) processed.
  diary id 1481965 (コミュニティ) processed.
  diary id 1479413 (OwLへ行きました。そして、T'sに参加出来ました。) processed.   
  done.

diary_id 2653068 から 2649753 の日記をダウンロードするには以下のように実行します。

::

  diarydump -f 2653068 -t 2649753
  Enter username and password
  user: <ここでユーザ名を入力します>
  pass: <ここでパスワードを入力します>
  diary id 2653068 (普段着) processed.
  diary id 2651906 (化粧品の代謝) processed.
  diary id 2649753 (メイクをしない高松 響子 がいる) processed.
  done.

Restriction
-----------

- 日記と同時に取得できるコメントは100件までです。100件以上のコメントがついている場合は先頭の100件が取得されます。


Notes
-----

- 自分の日記以外の diary_id を指定して取得することも可能ですが、相手の方に足跡を連続してつけることになるのでご注意ください。
