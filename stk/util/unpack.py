"""
unpack
---

unpack single or all files

:org:           Continental AG
:author:        Gerd-Joachim Hospes

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:33CEST $
"""
# Import Python Modules -------------------------------------------------------
import os
import fnmatch
import zipfile
import subprocess

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------
from stk.util.helper import deprecated

# Import Local Python Modules -------------------------------------------------

# Functions -------------------------------------------------------------------


def unzip_file(zipname, topath='.'):
    '''
    unzip given file (incl. path) to optional given path
    if no path is named use directory of zip file
    existing files are overwritten without asking
    :param zipname: name of file to unzip
    :param topath: opt. target path to unpack to, default current folder
    '''
    zip_ref = zipfile.ZipFile(zipname, 'r')
    zip_ref.extractall(topath)
    zip_ref.close()


def un7zip_file(zipname, topath=r'./', quiet='False'):
    '''
    unpack 7z package to given path using machine local installation of 7z
    if no path is given use directory of packed file
    already existing files are renamed and new versions unpacked
    :param zipname: file to unpack
    :param topath: opt. target path for unpacked files, default current folder
    :param quite: set True if 7z should print no output to screen
    '''
    # Windows version calling:
    sevenzip_exe = r"C:\Program Files\7-Zip\7z.exe"
    # call params:
    # x    : extract with path
    # -aot : overwrite, auto rename existing file
    # -y   : assume Yes on all queries
    expression = [sevenzip_exe, 'x', zipname, '-aot', '-y', r'-o' + topath]
    if quiet is True:
        subprocess.call(expression, stdout=subprocess.PIPE)
    else:
        subprocess.call(expression)


def unpack_all_files(zippath, topath=r'./', quiet='False'):
    '''
    unzip all *.zip & *.7z files found in given directory 'zippath'
    into same or optional named directory 'topath'
    :param zippath: path with zipped files to be unpacked
    :param topath: opt. target path to unpack the files to, default current folder
    :param quiet: opt. set True if 7z should suppress screen output
    '''
    for zipname in os.listdir(zippath):
        if fnmatch.fnmatch(zipname, '*.zip'):
            unzip_file(os.path.join(zippath, zipname), topath)
        if fnmatch.fnmatch(zipname, '*.7z'):
            un7zip_file(os.path.join(zippath, zipname), topath, quiet)


@deprecated('unzip_file')
def UnzipFile(zipname, topath='.'):  # pylint: disable=C0103
    """deprecated"""
    return unzip_file(zipname, topath)


@deprecated('un7zip_file')
def Un7zipFile(zipname, topath=r'./', quiet='False'):  # pylint: disable=C0103
    """deprecated"""
    return un7zip_file(zipname, topath, quiet)


@deprecated('unpack_all_files')
def UnpackAllFiles(zippath, topath=r'./', quiet='False'):  # pylint: disable=C0103
    """deprecated"""
    return unpack_all_files(zippath, topath, quiet)

# # support for other pack algorithms possible if needed

"""
CHANGE LOG:
-----------
$Log: unpack.py  $
Revision 1.1 2015/04/23 19:05:33CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.7 2015/01/23 21:44:21CET Ellero, Stefano (uidw8660) 
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 23, 2015 9:44:22 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.6 2014/03/16 21:55:53CET Hecker, Robert (heckerr) 
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:53 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.5 2013/06/11 17:21:55CEST Hospes, Gerd-Joachim (uidv8815)
add quiet option for 7z unpack
--- Added comments ---  uidv8815 [Jun 11, 2013 5:21:56 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.4 2013/03/01 15:29:09CET Hecker, Robert (heckerr)
Updates regarding pep8 styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 3:29:09 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/28 08:12:28CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:28 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/01/17 09:50:33CET Hospes, Gerd-Joachim (uidv8815)
7z unpack and mks log added, changed UnzipAllFiles to UnpackAllFiles to
show support of different zippers
--- Added comments ---  uidv8815 [Jan 17, 2013 9:50:33 AM CET]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
"""
