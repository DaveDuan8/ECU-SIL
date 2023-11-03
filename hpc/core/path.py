"""
path.py
----------

supporting path for win/lin
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import platform, stderr
from os import path, chmod
from re import match
from shutil import rmtree
from time import sleep

MSWIN = platform == "win32"
if MSWIN:
    from win32api import SetFileAttributes
    from win32con import FILE_ATTRIBUTE_NORMAL

# - import HPC modules -------------------------------------------------------------------------------------------------
from .tds import HPC_SHARES  # , HPC_STORAGE_MAP, LND_HEAD, BLR_HEAD, ABH_HEAD, FFM_HEAD, SHB_HEAD


# - functions ----------------------------------------------------------------------------------------------------------
if MSWIN:
    splitdrive = path.splitdrive  # pylint: disable=C0103

    def set_norm_attrib(fldr):
        """set normal file attribute"""
        SetFileAttributes(fldr, FILE_ATTRIBUTE_NORMAL)

else:  # pragma: nocover
    def splitdrive(name):
        """keep compatibility for linux..."""
        if name[0] == '/':  # is a 'UNC' path
            try:
                return match(r"(/\w+/\w+)(/.*)", name).groups()
            except Exception:
                pass
        return '', name

    def set_norm_attrib(fldr):
        """set normal file attribute"""
        chmod(fldr, 0o644)


def merge_path(p1, p2):
    """merge paths so that duplicates of end of p1 and start of p2 are unified"""
    for i in range(len(p1)):
        if p1[i:] == p2[:min(len(p2), len(p1[i:]))]:
            return path.join(p1[:i], p2)

    return path.join(p1, p2)


def on_rm_error(func, folder, _):
    """
    If the error is due to an access error (read only file)
    it attempts to remove read-only permission and then retries.

    If the error is for another reason it re-raises the error.
    """
    try:
        for _ in range(3):
            set_norm_attrib(folder)

            if func == rmtree:  # pylint: disable=W0143
                func(folder, onerror=on_rm_error)
            else:
                func(folder)
            break
    except Exception as ex:
        stderr.write("{!s}\n".format(ex))
        sleep(1)


def on_tree_error(func, fldr, _):
    """in case on error during folder removal"""
    set_norm_attrib(fldr)
    func(fldr)


# def repo_path():
#     """
#     aka repository path
#
#     :return: path to distribution path
#     :rtype: str
#     """
#     srv = LND_HEAD
#     loc_lookup = {"inblr": BLR_HEAD, "usabh": ABH_HEAD, "defrm": FFM_HEAD, "cnj": SHB_HEAD, "sgsgpl": SHB_HEAD}
#     try:
#         from win32com.client import GetObject  # pylint: disable=C0415
#
#         root = GetObject('LDAP://rootDSE')
#         srvn = 'LDAP://' + root.Get('dsServiceName')
#         ntds = GetObject(srvn)
#         site = GetObject(GetObject(GetObject(ntds.Parent).Parent).Parent)
#         loc = match(r"(cnj|[a-z]*)\d*", site.Get('cn').lower()).group(1)
#         srv = loc_lookup.get(loc, srv)
#     except Exception:  # lookup error as user is locked out???
#         from socket import gethostname  # pylint: disable=C0415
#
#         loc_lookup = {"OZ": BLR_HEAD, "AN": ABH_HEAD, "LS": FFM_HEAD, "IT": SHB_HEAD}
#         srv = loc_lookup.get(gethostname()[:2].upper(), srv)
#
#     return path.join(HPC_STORAGE_MAP[srv][1], "hpc", "HPC_Python")


def linux2win(folder):
    """
    convert folder path from linux to windows

    :param str folder: to convert from linux to windows path separator
    :return: windows folder path
    :rtype: str
    """
    return _os2os(folder, "linux", "win32")


def win2linux(folder):
    """
    convert folder path from windows to linux

    :param str folder: to convert from windows to linux path separator
    :return: linux folder path
    :rtype: str
    """
    if not folder:
        return None

    return _os2os(folder, "win32", "linux")


def _os2os(folder, src, dst):
    """
    convert a path from one OS to another OS

    :param str folder: folder to convert from (src)
    :param str src: OS source
    :param str dst: OS destination
    :return: folder path of dst
    :rtype: str
    """
    dfldr = folder.replace('/mnt/', '/datac/') if folder.startswith('/mnt/') else folder
    lfolder = dfldr.lower()
    for i, k in enumerate(HPC_SHARES[src]):
        if lfolder.startswith(k):
            return HPC_SHARES[dst][i] + dfldr[len(k):]\
                .replace(*(('\\', '/',) if src == "win32" or lfolder.startswith("http") else ('/', '\\',)))

    return folder
