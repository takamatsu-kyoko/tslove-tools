'''ダンプアプリケーションの基本的な機能を提供します'''

from typing import Any

from tslove.core.web import TsLoveWeb


class DumpApp():  # pylint: disable=R0903
    '''ダンプアプリケーションの基底クラス'''

    def __init__(self) -> None:
        self._config: Any = None
        self._web = TsLoveWeb(url='https://tslove.net/')
        self._page_info: dict = {}
