# -*- coding:utf-8 -*-
r"""
stk/cmd/del_sub_folders.py
--------------------------

**Delete all subfolders from a given path which matches a filter criteria.**

**Features:**
    - walks recursive through a all sub-folders starting from a given folder.
      and deletes all directories, which match a given Filter criteria.
    - Parse Order File
    - If no Filter is given, all subdirectories will be deleted.

**UseCase:**
 Typically used for a Simulation Job which has a StatisticCollector inside.
 In the Case, when a filed Task (or Job) will be requeued, the old results
 on the network will be deleted first, before the new ones will be created.
 To prevent from creating mixed results.

**Usage:**

del_sub_folders.py -o FolderToDelete -f FilterString

Parameters:
 -o FolderToDelete
    Folder which must be scanned for subfolders to delete.
    (e.g. "\\LIFS010\hpc\liss006\6453_ARS_SIM\2_Output\T00005")
 -f FilterString
    String, which describes a matching string, which must be inside the
    foldername, to delete the whole folder. (e.g. -f _CGStatistic)


:org:           Continental AG
:author:        Robert Hecker,
                Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:03:46CEST $
"""
# Import Python Modules --------------------------------------------------------
from optparse import OptionParser
import sys
import os
import shutil
import stat


# Defines ----------------------------------------------------------------------
ERR_OK = 0
ERR_INPUT_PATH_MISSING = -2
ERR_REMOVE_READ_ONLY_FLAG = -3


# Globals ----------------------------------------------------------------------
global Error
Error = ERR_OK


# Functions --------------------------------------------------------------------
def on_rm_error(func, path, exc_info):

    global Error
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    try:
        os.chmod(path, stat.S_IWRITE)
        os.unlink(path)
    except:
        Error = ERR_REMOVE_READ_ONLY_FLAG


def del_sub_folders(path, del_filter=None):
    """
    function which delete all subfolders on a given path, which match
    the filter criteria.

    :param path:       Input path which is used for delete subfolders.
    :type path:        string
    :param del_filter: Filter text, which is used for matching.
    :type del_filter:  string
    """
    global Error
    error = 0

    if path is None:
        print('path (Option -o) is missing')
        return ERR_INPUT_PATH_MISSING

    if not os.path.exists(path):
        print('input path "' + path + '" does not exist')
        return ERR_OK

    # List all Subdirectories inisde the given path
    for path_, subdirs, _ in os.walk(path):
        for subdir in subdirs:
            delete_sd = False

            # Check if Filter Criteria is matching
            if del_filter is not None:
                if del_filter in subdir:
                    delete_sd = True
            else:
                delete_sd = True

            if delete_sd:
                # When Filter is matching, perform the delete.
                subdir = os.path.join(path_, subdir)
                shutil.rmtree(subdir, ignore_errors=False, onerror=on_rm_error)
                if Error is not ERR_OK:
                    print "Error deleting folder: " + subdir
                    error = Error
                    Error = ERR_OK
                else:
                    print "Deleted folder: " + subdir

    return error


# Main Entry Point -------------------------------------------------------------
def main():
    """main function"""

    parser = OptionParser(usage="%prog [Options]")

    parser.add_option("-o",
                      dest="path",
                      default=None,
                      help="Folder to scan for subfolders to delete")
    parser.add_option("-f",
                      dest="filter",
                      default=None,
                      help="String filter (e.g. -f _CGStatistic)")

    opt = parser.parse_args()[0]

    return del_sub_folders(opt.path, opt.filter)

if __name__ == "__main__":
    sys.exit(main())

"""
CHANGE LOG:
-----------
$Log: del_sub_folders.py  $
Revision 1.1 2015/04/23 19:03:46CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.12 2014/09/01 13:54:45CEST Hecker, Robert (heckerr) 
Added feature to delete also files which have teh read only flag set.
--- Added comments ---  heckerr [Sep 1, 2014 1:54:46 PM CEST]
Change Package : 260554:1 http://mks-psad:7002/im/viewissue?selection=260554
Revision 1.11 2014/07/17 10:00:51CEST Hecker, Robert (heckerr)
Removed wrong Error Code output.
--- Added comments ---  heckerr [Jul 17, 2014 10:00:52 AM CEST]
Change Package : 249341:1 http://mks-psad:7002/im/viewissue?selection=249341
Revision 1.10 2014/06/13 09:22:23CEST Hecker, Robert (heckerr)
Some more updates in epydoc.
--- Added comments ---  heckerr [Jun 13, 2014 9:22:24 AM CEST]
Change Package : 238264:1 http://mks-psad:7002/im/viewissue?selection=238264
Revision 1.9 2014/06/12 16:38:41CEST Hecker, Robert (heckerr)
Updated epydoc description.
--- Added comments ---  heckerr [Jun 12, 2014 4:38:42 PM CEST]
Change Package : 238257:1 http://mks-psad:7002/im/viewissue?selection=238257
Revision 1.8 2014/04/24 22:52:50CEST Hecker, Robert (heckerr)
REmoved wrong Error Code, created UnitTest.
--- Added comments ---  heckerr [Apr 24, 2014 10:52:51 PM CEST]
Change Package : 233029:1 http://mks-psad:7002/im/viewissue?selection=233029
Revision 1.7 2014/04/15 14:02:35CEST Hecker, Robert (heckerr)
some adaptions to pylint.
--- Added comments ---  heckerr [Apr 15, 2014 2:02:35 PM CEST]
Change Package : 231472:1 http://mks-psad:7002/im/viewissue?selection=231472
Revision 1.6 2013/09/26 19:13:27CEST Hecker, Robert (heckerr)
Removed some pep8 Errors.
--- Added comments ---  heckerr [Sep 26, 2013 7:13:27 PM CEST]
Change Package : 197303:1 http://mks-psad:7002/im/viewissue?selection=197303
Revision 1.5 2013/09/26 18:22:56CEST Hecker, Robert (heckerr)
Added Error to check jenkins.
--- Added comments ---  heckerr [Sep 26, 2013 6:22:56 PM CEST]
Change Package : 197303:1 http://mks-psad:7002/im/viewissue?selection=197303
Revision 1.4 2013/09/26 17:42:22CEST Hecker, Robert (heckerr)
Removed some Pylint Errors.
--- Added comments ---  heckerr [Sep 26, 2013 5:42:23 PM CEST]
Change Package : 197303:1 http://mks-psad:7002/im/viewissue?selection=197303
Revision 1.3 2013/09/25 09:20:19CEST Hecker, Robert (heckerr)
Removed some Errors and corrected stk import.
--- Added comments ---  heckerr [Sep 25, 2013 9:20:19 AM CEST]
Change Package : 197303:1 http://mks-psad:7002/im/viewissue?selection=197303
"""
