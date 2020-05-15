tslove-tools
============

`T's LOVE <http://tslove.net>`_ に関連するツール達

Description
-----------

T's Love 用に作られたツール群です。以下のツールがあります。

imechen (`doc <https://github.com/takamatsu-kyoko/tslove-tools/blob/master/doc/imechen.rst>`_)
  T's LOVEのプロフィール画像を差し替えます

diarydump (`doc <https://github.com/takamatsu-kyoko/tslove-tools/blob/master/doc/diarydump.rst>`_)
  T's LOVEの日記を一括してダウンロードします

各ツールの説明は doc ディレクトリの内容を確認してください。

また、diarydumpについてPythonのインストールからコマンドの実行までを説明した文章があるので必要に応じてご覧ください。

- Windows用

  - `QuickSetupGuide-windows <https://github.com/takamatsu-kyoko/tslove-tools/wiki/QuickSetupGuide-windows>`__

Requirement
-----------

- python3
- requests
- beautifulsoup4
- pillow

開発環境では以下も必要

- pytest

Installation
------------

通常のインストール ::

  pip install <path>

開発環境でのインストール ::

  pip install -e <path>[develop]

Licence
-------

`MIT <https://github.com/takamatsu-kyoko/tslove-tools/blob/master/LICENSE>`_

Author
------

`高松 響子 <https://github.com/takamatsu-kyoko/>`_
