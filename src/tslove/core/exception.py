'''Exceptionモジュール

tslove-tools全般で使用する例外
'''


class RetryCountExceededError(RuntimeError):
    '''再試行回数を超過した際に送出されます'''
