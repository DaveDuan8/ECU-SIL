r"""
bpl_func.py
-----------

functions, helping the user to manipulate bpl files
"""
# pylint: disable=C0103
# - import Python modules ----------------------------------------------------------------------------------------------
from os import getcwd
from os.path import join

# - import HPC modules -------------------------------------------------------------------------------------------------
from .base import Bpl


# - functions ----------------------------------------------------------------------------------------------------------
def create(entries, path):
    """
    create a single bpl-file out of some given bpllistentries.

    :param list[`BplListEntry`] entries: list of BplListEntries
    :param str path:    path to the file to be created.
    """
    with Bpl(path, "w") as out_bpl:  # pylint: disable=E1129
        for entry in entries:
            out_bpl.append(entry)


def split(bplfilepath, task_size, outfolder=getcwd()):
    """
    Split a bpl-file into bpl's with the given task_size which
    contians the original section information.

    :param str bplfilepath: Filepath(url) to the bpl file..
    :param str task_size: Number of recordings per file.
    :param str outfolder: Folder to store the generated bpl files.
    :return: Array of created bpl files.
    :rtype: list of bpl paths.
    """
    bpllist = []

    out_bpl = None
    task_cnt = 1
    cnt = task_size

    with Bpl(bplfilepath) as bpl:  # pylint: disable=E1129
        for item in bpl:
            if cnt == task_size:
                out_bpl = Bpl(join(outfolder, "T%05d.bpl" % task_cnt))
                bpllist.append(out_bpl.filepath)    # pylint: disable=E1101
                task_cnt += 1
            out_bpl.append(item)
            cnt -= 1
            if cnt == 0:
                out_bpl.write()
                cnt = task_size

    if out_bpl is not None and cnt > 0:
        out_bpl.write()

    return bpllist
