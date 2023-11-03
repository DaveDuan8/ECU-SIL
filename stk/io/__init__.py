"""
stk/io/__init__.py
-------------------

Classes for io handling.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:29CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------

from . req_data import RequirementsData
from . bsig import BsigReader

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:04:29CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/io/project.pj
Revision 1.7 2014/10/14 11:41:37CEST Hecker, Robert (heckerr) 
Removed deprecated import of dlm.
--- Added comments ---  heckerr [Oct 14, 2014 11:41:38 AM CEST]
Change Package : 271208:1 http://mks-psad:7002/im/viewissue?selection=271208
Revision 1.6 2014/10/13 11:48:18CEST Hecker, Robert (heckerr)
Corrected relative import.
Revision 1.5 2013/03/22 08:24:34CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:34 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/03/01 16:38:33CET Hecker, Robert (heckerr)
Update regarding Pep8 Styleguide.
--- Added comments ---  heckerr [Mar 1, 2013 4:38:34 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/26 17:11:40CET Hecker, Robert (heckerr)
Added reference to dlm
--- Added comments ---  heckerr [Feb 26, 2013 5:11:41 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/11 10:33:50CET Raedler, Guenther (uidt9430)
- added bsig from stk 1.0 and req_data from etk/vpc
--- Added comments ---  uidt9430 [Feb 11, 2013 10:33:50 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/01/23 07:59:40CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/io/project.pj
"""
