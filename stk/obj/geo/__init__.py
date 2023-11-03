"""
stk/obj/geo/__init__.py
-------------------

Classes for Object geometry description and calculations

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:53CEST $
"""
# Import Python Modules --------------------------------------------------------

# Add PyLib Folder to System Paths ---------------------------------------------

# Import STK Modules -----------------------------------------------------------

# Import Local Python Modules --------------------------------------------------
from .point import *
from .rect import *

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:04:53CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/geo/project.pj
Revision 1.4 2014/03/26 15:05:08CET Hecker, Robert (heckerr) 
Updates for python 3 support.
--- Added comments ---  heckerr [Mar 26, 2014 3:05:08 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.3 2013/12/03 17:33:08CET Sandor-EXT, Miklos (uidg3354)
pylint fix
--- Added comments ---  uidg3354 [Dec 3, 2013 5:33:08 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.2 2013/03/22 08:24:33CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:34 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.1 2013/02/11 10:50:00CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/
    stk/obj/geo/project.pj
"""
