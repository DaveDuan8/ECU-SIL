# -*- coding:utf-8 -*-
r"""
bpl_online_offline_split
------------------------

**Checks if all rec files in a bpl are online**
and creates two new bpl files with the online and offline rec files

**Features:**
    - Open Existing bpl file and check every entry if file is online (stored where listed) or offline.
    - Supported bpl file formats are:

        - ``*.bpl``
        - ``*.ini``
        - ``*.txt``

**UseCase:**

Check which recordings are online or offline,
e.g. before HPC submits or for Datamanagement purposes.

The outcome are two bpl files: one with the online urls inside,
and one with the offline files inside.

**Usage:**

.. python::

    bpl_online_offline_split -i path\to\mylist.bpl

creates ``path\to\mylist_online.bpl`` and ``path\to\mylist_offline.bpl``

Parameters:
    -i InputFile
        The bpl file listing all ``*.rec`` files to check.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/09/19 15:18:36CEST $
"""
# Import Python Modules --------------------------------------------------------
import sys
import os
import win32con
import win32file
from optparse import OptionParser
import traceback

# Add PyLib Folder to System Paths ---------------------------------------------
STK_FOLDER = os.path.abspath(os.path.join(os.path.split(__file__)[0], r"..\.."))

if STK_FOLDER not in sys.path:
    sys.path.append(STK_FOLDER)

from stk.mts.bpl import bpl

# Defines ----------------------------------------------------------------------
ERR_OK = 0
ERR_ERROR = -200
ERR_INPUT_FILE_MISSING = -201
ERR_INPUT_FILE_DOES_NOT_EXIST = -202
ERR_FILE_NOT_FOUND = -203

# Definies ---------------------------------------------------------------------


# Functions --------------------------------------------------------------------
def fileattributeisset(filename, fileattr):
    """
    Check if a given Fileattribute is set.

    :return: Inforamtion if Fileattribute is set.
    :rtype: boolean
    """
    return bool(win32file.GetFileAttributes(filename) & fileattr)


def is_file_offline(filename):
    """
    check if the given file has the fileattribute "OFFLINE" set.

    :param filename: url to teh file to check.
    :type filename: string
    """
    filename = bpl.lifs010s_to_lifs010(filename)

    if os.path.isfile(filename):
        return fileattributeisset(filename, win32con.FILE_ATTRIBUTE_OFFLINE)
    else:
        raise IOError


def bpl_offline_splitter(input_file_path):
    """
    Check all entries in a given input file if the listed files are
    online or offline, and creates two output files in the same folder.
    """
    error = ERR_OK

    in_bpl = bpl.Bpl(input_file_path)

    base_file_name = os.path.splitext(os.path.split(input_file_path)[1])[0]
    file_ext = os.path.splitext(input_file_path)[1]

    bpl_arch = bpl.Bpl(os.path.join(os.path.split(input_file_path)[0],
                                    base_file_name + "_offline" + file_ext))
    bpl_online = bpl.Bpl(os.path.join(os.path.split(input_file_path)[0],
                                      base_file_name + "_online" + file_ext))

    bpllist = in_bpl.read()

    for bplentry in bpllist:
        try:
            if is_file_offline(str(bplentry)):
                # File is Archived
                print("Offline: %s" % (str(bplentry)))
                bpl_arch.append(bplentry)
            else:
                # File is not Archived
                print("Online:  %s" % (str(bplentry)))
                bpl_online.append(bplentry)
        except IOError:
            error = ERR_FILE_NOT_FOUND
            print("FileNotAvailable:   %s" % (str(bplentry)))

    bpl_arch.write()
    bpl_online.write()

    return error


def main():
    """main function"""

    error = 0
    version = "Bpl Online Offline Splitter Version 1.0.0"

    parser = OptionParser(usage="%prog [Options]",
                          version=version)
    parser.add_option("-i",
                      "--InputFile",
                      dest="input_file",
                      default="",
                      help="Input *.bpl file, which must be used to process")

    opt = parser.parse_args()

    if(opt[0].input_file == ""):
        error = ERR_INPUT_FILE_MISSING

    if(error is ERR_OK and os.path.isfile(opt[0].input_file) is False):
        error = ERR_INPUT_FILE_DOES_NOT_EXIST

    if(error == ERR_OK):
        try:
            error = bpl_offline_splitter(opt[0].input_file)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            error = ERR_ERROR

    if error != ERR_OK:
        print("\n\bpl_online_offline_spliter error:" + str(error))

    return error


if __name__ == '__main__':
    sys.exit(main())


"""
CHANGE LOG:
-----------
$Log: bpl_online_offline_split.py  $
Revision 1.3 2016/09/19 15:18:36CEST Hospes, Gerd-Joachim (uidv8815) 
fix docu
Revision 1.2 2016/08/16 16:01:44CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.1 2015/04/23 19:03:42CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.2 2014/07/15 09:38:16CEST Hecker, Robert (heckerr)
Added one more Errorcode, and improved path check.
--- Added comments ---  heckerr [Jul 15, 2014 9:38:16 AM CEST]
Change Package : 248675:1 http://mks-psad:7002/im/viewissue?selection=248675
Revision 1.1 2014/07/11 16:53:23CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/cmd/project.pj
"""
