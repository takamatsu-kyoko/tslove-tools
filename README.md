# tslove-tools

[T's LOVE](http://tslove.net) に関連するツール達

## Description

T's Love 用に作られたツール群です。以下のツールがあります。

- [diarydump](doc/diarydump.md): T's LOVEの日記を一括してダウンロードします

各ツールの説明はリンク先の内容を確認してください。

>[!NOTE]
> 以前公開していた `imechen` については廃止・非公開としました。

## Requirement

- python3
- requests
- beautifulsoup4
- pillow

## Installation

>[!IMPORTANT]
> tslove-tools は Python というプログラム言語で作られています。各ツールの実行には事前にPythonのインストールが必要です。
>
> 現時点で tslove-tools のリポジトリ内に Python のインストール方法をご案内するドキュメントはありません。
> (以前ご案内していた QuickSetupGuide は内容が古くなったため非推奨です)

1. [最新版のリリースページ](https://github.com/takamatsu-kyoko/tslove-tools/releases/latest)より、tslove_tools-X.Y.Z-py3-none-any.whl をダウンロードしてください。(X.Y.Zの箇所は実際のバージョン番号に読み替えてください)
2. インストール
   ```sh
   pip install tslove_tools-X.Y.Z-py3-none-any.whl
   ```
3. 各ツールの使い方はそれぞれのドキュメントを参照してください

## Licence

[MIT](https://github.com/takamatsu-kyoko/tslove-tools/blob/master/LICENSE)

## Author

[高松 響子](https://github.com/takamatsu-kyoko/)
