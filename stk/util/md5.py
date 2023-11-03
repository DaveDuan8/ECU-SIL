"""
stk/util/md5
------------

MD5 Checksum calculation

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:32CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath, walk
from hashlib import sha256, md5 as hlmd5
from fnmatch import translate
from re import match

# - import STK modules ------------------------------------------------------------------------------------------------
from ..error import StkError
from .helper import deprecated


# - functions ---------------------------------------------------------------------------------------------------------
def checksum(files, length=None, algo=None, strings=False, ignore=None):
    """does a checksum on given files.
    files are sorted beforehand doing hash, in case of directories they are sorted as well
    as their subdirectories. So, it's going recurse.

    For limiting the length of big files you can specify an integer or special name
    ``fasthash`` which is 1024 bytes or ``contenthash`` which is used for DB storages
    and is of maxlength 120000kB, but reduced to half of it if still longer than file size.

    If you set strings to True, it'll assume, given files are strings from which hashing
    should be done.

    Ignore option specifies a string or list of dir / file names which should be ignored,
    e.g. ['*.dll', '*.doc']

    :param files: destination folder or file or list of files to do hashing from
    :type files: str | list
    :param length: maximum length of each file to read in, for doing a ``fasthash``,
                  we usually grab first 1024 bytes, for ``contenthash``, we're
                  going for first 128000000 bytes, default is None to read out whole
    :type length: int | long
    :param algo: which algo to use, if None given, we're using sha256, others
                 provided by hashlib are: md5(), sha1(), sha224(), sha384() and sha512(),
                 also have a look to https://docs.python.org/2/library/hashlib.html
    :param strings: if set to true assume given files are supposed to be strings to be hashed directly
    :type strings: bool
    :param ignore: list of files / folders to be ignored (only if strings is False)
    :type ignore: str | list
    :return: hex value of algo output
    :rtype: str
    """
    if type(files) not in (tuple, list):  # put files into list
        files = [files]
    if not strings and not all((opath.exists(i) for i in files)):  # check for existance
        raise StkError("one or more path / file do not exist!")

    specialhash = (("fasthash", "contenthash",), (1024, 128000000L,),)
    if (type(length) not in (type(None), str, int, long) or
            type(length) == str and length not in specialhash[0] or
            type(length) == int and length < 0):
        raise StkError("'length' parameter is wrong!")
    elif length == specialhash[0][0]:
        length = specialhash[1][0]

    if algo is None:
        algo = sha256()
    elif not all((hasattr(algo, 'update'), hasattr(algo, 'hexdigest'))):
        raise StkError("'algo' doesn't seem to be a valid hash algo!")

    if type(ignore) not in (tuple, list, type(None)):
        ignore = [ignore]

    def do_checksum(dirname, filenames, algo, size, ignores):
        """adds given dir / filenames to hash
        """
        for filename in sorted(filenames):
            path = opath.join(dirname, filename)
            if path not in ignores and opath.isfile(path):  # take care of ignored items
                file_size = opath.getsize(path)
                if file_size == 0:
                    continue
                mx_size = size
                if mx_size is None:
                    mx_size = file_size
                elif size == specialhash[0][1]:
                    mx_size = specialhash[1][1]
                    while file_size <= mx_size:
                        mx_size /= 2
                with open(path, 'rb') as fptr:
                    step = 1024  # read in steps of 1024 (more effective)
                    for i in xrange(0, mx_size, step):
                        algo.update(fptr.read(min(i + step, mx_size) - i))

    if strings:
        for strn in files:
            algo.update(strn[:len(strn) if length is None else
                        specialhash[1][1] if length == specialhash[0][1] else length])
    else:
        for fname in sorted(files):
            excludes = [] if ignore is None else ignore
            excludes = r'|'.join([translate(x) for x in excludes]) or r'$.'

            if opath.isfile(fname):
                do_checksum(opath.dirname(fname), [opath.basename(fname)], algo, length, excludes)
            else:
                all_things = {}
                for root, dirs, files in walk(fname):
                    # exclude dirs
                    dirs[:] = [opath.join(root, d) for d in dirs]
                    dirs[:] = [d for d in dirs if not match(excludes, d)]

                    # exclude files
                    files = [opath.join(root, f) for f in sorted(files)]
                    files = [f for f in files if not match(excludes, f)]

                    all_things[root] = files

                for thing in sorted(all_things):
                    do_checksum(thing, all_things[thing], algo, length, [])

    return algo.hexdigest()


@deprecated('checksum')
def create_from_string(str_val, algo=None):
    """
    Creates a MD5 Checksum from a given string

    :param str_val:   Input string to calc MD5 checksum for
    :type str_val:    string
    :return:          MD5 Checksum
    :author:          Robert Hecker
    """
    return checksum(str_val, algo=hlmd5() if algo is None else algo, strings=True)


@deprecated('checksum')
def create_from_file(file_path, algo=None):
    """
    Creates a MD5 Checksum from an whole File

    :param file_path:    Input File to calc MD5 checksum for
    :return:            MD5 Checksum
    :author:            Robert Hecker
    """
    return checksum(file_path, algo=hlmd5() if algo is None else algo)


@deprecated('checksum')
def create_from_folder(folder_path, ignorelist=None):
    """
    calculates md5 checksum recursing through subfolders

    :param folder_path: directory to start
    :param ignorelist:  optional list of folder and file names to ignore
                        e.g. ['doc', '*.bak']
    :return:            md5 checksum
    """
    return checksum(folder_path, ignore=ignorelist)


@deprecated('checksum')
def CreateFromString(str_val, md5=None):  # pylint: disable=C0103
    """
    :deprecated: use `create_from_string` instead
    """
    return checksum(str_val, algo=hlmd5() if md5 is None else md5, strings=True)


@deprecated('checksum')
def CreateFromFile(file_path, algo=None):  # pylint: disable=C0103
    """
    :deprecated: use `create_from_file` instead
    """
    return checksum(file_path, algo=hlmd5() if algo is None else algo)


@deprecated('checksum')
def CreateFromFolder(folder_path, ignorelist=None):  # pylint: disable=C0103
    """
    :deprecated: use `create_from_folder` instead
    """
    return checksum(folder_path, algo=hlmd5(), ignore=ignorelist)


"""
$Log: md5.py  $
Revision 1.1 2015/04/23 19:05:32CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.13 2015/01/26 16:51:35CET Mertens, Sven (uidv7805) 
default algo is missing
--- Added comments ---  uidv7805 [Jan 26, 2015 4:51:35 PM CET]
Change Package : 299224:1 http://mks-psad:7002/im/viewissue?selection=299224
Revision 1.12 2015/01/26 14:16:58CET Mertens, Sven (uidv7805)
update to one common function
Revision 1.11 2015/01/23 13:01:08CET Mertens, Sven (uidv7805)
providing checksum function for one or more files / directories
Revision 1.10 2014/07/29 18:25:39CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint error W0102 and some others
--- Added comments ---  uidv8815 [Jul 29, 2014 6:25:39 PM CEST]
Change Package : 250927:1 http://mks-psad:7002/im/viewissue?selection=250927
Revision 1.9 2014/03/24 21:56:58CET Hecker, Robert (heckerr)
Adapted to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:56:58 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.8 2014/03/16 21:55:55CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:56 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.7 2013/08/08 09:05:10CEST Hecker, Robert (heckerr)
Addd new md5 Calculation Function.
--- Added comments ---  heckerr [Aug 8, 2013 9:05:11 AM CEST]
Change Package : 192878:1 http://mks-psad:7002/im/viewissue?selection=192878
Revision 1.6 2013/01/16 17:11:53CET Hospes, Gerd-Joachim (uidv8815)
use hashlib library instead of old md5
--- Added comments ---  uidv8815 [Jan 16, 2013 5:11:53 PM CET]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.5 2012/12/14 11:21:20CET Hospes, Gerd-Joachim (uidv8815)
add ignorelist to test_CreateFromFolder
--- Added comments ---  uidv8815 [Dec 14, 2012 11:21:20 AM CET]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.4 2012/12/11 14:39:16CET Hospes, Gerd-Joachim (uidv8815)
fix CreateFromFolder by using sorted lists
--- Added comments ---  uidv8815 [Dec 11, 2012 2:39:18 PM CET]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.3 2012/12/05 13:49:54CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:54 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 09:14:57CET Hecker, Robert (heckerr)
Adapted code to pep8.
--- Added comments ---  heckerr [Dec 5, 2012 9:14:57 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 18:01:47CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
