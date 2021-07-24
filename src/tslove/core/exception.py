'''Exceptionモジュール

tslove-tools全般で使用する例外
'''


class TsLoveToolsException(Exception):
    '''tslove-tools例外の基底クラス'''


class WebAccessError(TsLoveToolsException):
    '''コンテンツの取得に失敗した際に送出されます'''


class RequestError(WebAccessError):
    '''requestsパッケージのエラーをラッピングします'''


class RetryCountExceededError(WebAccessError):
    '''再試行回数を超過した際に送出されます'''


class NoSuchDiaryError(TsLoveToolsException):
    '''指定された日記が存在しなかった際に送出されます'''
