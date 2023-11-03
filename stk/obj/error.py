"""
stk/error.py
------------

This Module contains the General Exception Handling Methods, which are available inside the stk.

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:47CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------
from sys import _getframe
from os import path as oPath

from stk import error

# Defines -------------------------------------------------------------------------------------------------------------
ERR_OK = 0
"""Code for No Error"""
ERR_UNSPECIFIED = 1
"""Code for an unknown Error"""

# Classes -------------------------------------------------------------------------------------------------------------


class AdasObjectLoadError(error.StkError):
    """
    Exception Class for all HPC Exceptions.

    :author:        Robert Hecker
    :date:          04.09.2013
    """
    def __init__(self, msg, errno=error.ERR_UNSPECIFIED):
        """
        Init Method of Exception class

        :param msg:   Error Message string, which explains the user was went wrong.
        :type msg:    string
        :param errno: unique number which represents a Error Code inside the Package.
        :type errno:  integer

        :author:      Robert Hecker
        :date:        04.09.2013
        """
        error.StkError.__init__(self, msg, errno)

"""
CHANGE LOG:
-----------
$Log: error.py  $
Revision 1.1 2015/04/23 19:04:47CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.2 2015/02/06 08:10:48CET Mertens, Sven (uidv7805) 
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:10:49 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.1 2013/12/03 14:12:03CET Sandor-EXT, Miklos (uidg3354)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
"""
