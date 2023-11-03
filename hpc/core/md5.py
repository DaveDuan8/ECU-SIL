"""
md5.py
------

*MD5 checksum calculation utilities*
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from os import listdir
from os.path import join, isdir, isfile
from hashlib import md5, sha256
from fnmatch import filter as fnfilter


# - functions ----------------------------------------------------------------------------------------------------------
def create_from_string(str_val):
    """
    create a MD5 checksum from a given string

    :param str str_val: input string to calc checksum for
    :return: sha256 checksum
    :rtype: str
    """
    algo = sha256()
    algo.update(str_val.encode())
    return algo.hexdigest()


def create_from_file(file_path, algo=None):
    """
    create a MD5 Checksum from an whole File

    :param list file_path: input file(s) to calc checksum for
    :param function algo: hash function
    :return: checksum
    :rtype: str
    """
    if algo is None:
        algo = sha256()

    if not isinstance(file_path, (list, tuple)):
        file_path = [file_path]

    for i in file_path:
        with open(i, "rb") as fp:
            while True:
                block = fp.read(2048)
                if not block:
                    break
                algo.update(block)

    return algo.hexdigest()


def create_from_folder(folder_path, ignorelist=None):
    r"""
    calculate md5 checksum recursing through subfolders

    :param str folder_path: directory to start
    :param list ignorelist:  optional list of folder and file names to ignore, e.g. ['doc', '\*.bak']
    :return: md5 checksum
    :rtype: str
    """
    if ignorelist is None:
        ignorelist = []
    md5_obj = md5()
    digest = []
    absfolderlist = [folder_path]

    for i in absfolderlist:
        # check for SubFolders
        tmp = [k for k in listdir(i) if isdir(join(i, k))]
        for j in sorted(tmp):
            if j not in ignorelist:
                absfolderlist.append(join(i, j))
        # Check for Files
        fileset = {k for k in fnfilter(listdir(i), "*.*") if isfile(join(i, k))}
        for ignore in ignorelist:
            fileset = fileset - set(fnfilter(fileset, ignore))
        for j in sorted(fileset):
            path = join(i, j)
            digest = create_from_file(path, md5_obj)

    return digest
