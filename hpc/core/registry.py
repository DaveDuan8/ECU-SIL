"""
registry.py
-----------

windows registry wrapper to make our live easier
"""
# pylint: disable=W0611
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import platform
from itertools import count
from six import PY2

MSWIN = platform == "win32"
if MSWIN:
    from winreg import OpenKey, CloseKey, QueryValueEx, EnumValue, EnumKey, KEY_READ, KEY_ALL_ACCESS, \
        HKEY_LOCAL_MACHINE, HKEY_CLASSES_ROOT, HKEY_CURRENT_USER
else:
    KEY_READ = HKEY_CLASSES_ROOT = HKEY_LOCAL_MACHINE = None

RegKeyNotFoundError = WindowsError if PY2 else FileNotFoundError


# - functions / classes ------------------------------------------------------------------------------------------------
class WinReg(object):
    """windows registry wrapper"""

    def __init__(self, key, subkey, access=KEY_READ):
        r"""
        copy src to dst with some arguments

        :param str key: registry base key
        :param str subkey: key to open
        :param int access: access permission
        """
        if PY2:
            self._key = OpenKey(key, subkey, 0, access)
        else:
            self._key = OpenKey(key, subkey, access=access)
        self._items = self._keys = None

    def __enter__(self):
        """support with statement"""
        return self

    def __exit__(self, *_):
        """close the key"""
        CloseKey(self._key)

    def get(self, item, default=None):
        """get the key value"""
        try:
            return QueryValueEx(self._key, item)[0]
        except RegKeyNotFoundError:
            return default

    def items(self):
        """
        iterate over my items, except internals

        :return: list of key/values
        :rtype: list
        """
        if self._items is not None:
            return self._items

        self._items = []
        for i in count():
            try:
                self._items.append(EnumValue(self._key, i)[:2])
            except OSError:
                break
        return self._items

    iteritems = items

    def keys(self):
        """
        iterate over my (sub-)keys, except internals

        :return: list of key/values
        :rtype: list
        """
        if self._keys is not None:
            return self._keys

        self._keys = []
        for i in count():
            try:
                self._keys.append(EnumKey(self._key, i))
            except OSError:
                break
        return self._keys
