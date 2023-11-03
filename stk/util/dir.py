"""
dir
---

documentation of dir
docu docu

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:29CEST $
"""
# Import Python Modules -------------------------------------------------------
from os import listdir, path
from fnmatch import filter

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------

# local Functions -------------------------------------------------------------


def list_dir_names(folder):
    """
    Function returns all DirectoryNames as List, which
    are found inside Folder. Returns empty list for not existing dir.

    :param folder:     Folder
    :return:           DirNameList
    :author:           Robert Hecker
    """
    folder_names = []
    try:
        folder_names = listdir(folder)
    except:
        return []

    filtered_folder_names = []
    for item in folder_names:
        if not path.isfile(str(folder + "/" + item)):
            filtered_folder_names.append(item)
    return filtered_folder_names


def list_file_names(folder, file_filter="*.*"):
    """
    All FileNames will be returned as List.
    Returns empty list for not existing dir.

    :param folder: folder to search
    :param file_filter: file filter (e.g. *.rec)

    :return:           FileNameList
    :author:           Robert Hecker
    """
    try:
        file_names = listdir(folder)
    except:
        return []
    file_names = list(filter(file_names, file_filter))
    return file_names

"""
CHANGE LOG:
-----------
$Log: dir.py  $
Revision 1.1 2015/04/23 19:05:29CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.8 2015/02/26 16:15:34CET Mertens, Sven (uidv7805) 
docu update
--- Added comments ---  uidv7805 [Feb 26, 2015 4:15:35 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.7 2014/03/24 21:49:39CET Hecker, Robert (heckerr)
Adapted to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:49:39 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.6 2014/03/16 21:55:56CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:56 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.5 2013/03/28 15:25:17CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:17 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/03/28 09:33:19CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:19 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.3 2012/12/05 13:49:54CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:54 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 11:30:47CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 11:30:48 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 18:01:45CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
