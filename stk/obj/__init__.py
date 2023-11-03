"""
stk/obj/__init__.py
-------------------

Classes for ADAS Object Handling

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:44CEST $
"""
# Import Python Modules --------------------------------------------------------

# Add PyLib Folder to System Paths ---------------------------------------------

# Import STK Modules -----------------------------------------------------------

# Import Local Python Modules --------------------------------------------------
from . import geo
from . import adas_objects
from .ego import EgoMotion

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:04:44CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.7 2014/04/29 10:26:29CEST Hecker, Robert (heckerr) 
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:29 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.6 2014/02/06 16:15:01CET Sandor-EXT, Miklos (uidg3354)
OrderedDict
--- Added comments ---  uidg3354 [Feb 6, 2014 4:15:01 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.5 2014/01/24 10:55:23CET Sandor-EXT, Miklos (uidg3354)
todo added for python revision update
--- Added comments ---  uidg3354 [Jan 24, 2014 10:55:23 AM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.4 2013/12/03 13:42:04CET Sandor-EXT, Miklos (uidg3354)
pythonext added
--- Added comments ---  uidg3354 [Dec 3, 2013 1:42:05 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.3 2013/05/14 10:30:48CEST Ibrouchene, Nassim (uidt5589)
Added import of EgoMotion class.
--- Added comments ---  uidt5589 [May 14, 2013 10:30:48 AM CEST]
Change Package : 182606:1 http://mks-psad:7002/im/viewissue?selection=182606
Revision 1.2 2013/03/22 08:24:33CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:33 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.1 2013/02/11 10:49:58CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/
    stk/obj/project.pj
"""
