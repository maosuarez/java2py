"""java2py: traductor de Java a Python para estudiar, sin IA.

    >>> from java2py import translate
    >>> print(translate('int doble(int x) { return x * 2; }'))
    def doble(x: int) -> int:
        return x * 2
"""

from .translator import TranslationResult, translate, translate_detailed, translate_file

__version__ = "0.2.0"
__all__ = ["translate", "translate_detailed", "translate_file", "TranslationResult", "__version__"]
