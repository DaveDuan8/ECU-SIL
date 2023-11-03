"""
url
---

utility functions for url handling.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:34CEST $
"""
# Import Python Modules -------------------------------------------------------

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------

# local Functions -------------------------------------------------------------


def remove_fqn(input_url):
    """
    parses the input url and remove the Full Qualified URL Name if given.
    returns the modified url.

    :param input_url: UNC path to File
    :type input_url:  string
    :return:          Stripped UNC Path without FQN
    :rtype:           string
    """
    items = input_url.split('\\')

    items[2] = items[2].split('.')[0]

    items = items[1:]

    # Build new path
    result = ''
    for item in items:
        result += '\\'
        result += item

    return result

"""
CHANGE LOG:
-----------
$Log: url.py  $
Revision 1.1 2015/04/23 19:05:34CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.1 2014/11/11 11:07:52CET Hecker, Robert (heckerr) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
