"""Viper decorators and CPython buffer views for the desktop simulator.

On Pico, Viper recognises ptr8/ptr16/ptr32 as compiler intrinsics. The Python
functions below are only executed by the desktop fallback. ptr32 uses signed
words because callers explicitly cast its reads to Viper's signed int type.
"""
try:
    import micropython
except ImportError:
    class micropython:
        @staticmethod
        def viper(function):
            return function


def ptr8(buffer):
    return memoryview(buffer).cast('B')


def ptr16(buffer):
    return memoryview(buffer).cast('B').cast('H')


def ptr32(buffer):
    return memoryview(buffer).cast('B').cast('i')
