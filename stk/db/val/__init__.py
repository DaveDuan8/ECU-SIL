"""
stk/db/val/__init__.py
----------------------

This Subpackage provides a complete Interface VAL Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseValResDB`

**See also relevant Classes:**

  - `db_common`

**To get more information about the usage of the Object database interface, you can also check following Links:**

ADAS Database API Documentation.
    * This Document

Enterprise Architecture design and document linked at
     * http://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation/page/RQ%20Engineering%20for%20Tools

Wiki Server with FAQ's
     * https://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation

Module test Code under
    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5fapi/project.pj&selection=test%5fapi.py

    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5fval/project.pj&selection=test%5fval.py


**To use the val package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.val import BaseValResDB

    # Import error tolerance global constant
    from stk.db import ERROR_TOLERANCE_MED

    # Get a instance of Object DB interface.
    valdb = BaseValResDB(db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get result with known id from database
    results = valdb.get_result(tr_id=12)

    # Terminate val database
    valdb.close()

    ...

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:28CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------
from . val import BaseValResDB      # base class providing common catalog interface methods
from stk.db.val.val import PluginValResDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.3 2016/08/16 12:26:28CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.2 2015/07/14 09:32:40CEST Mertens, Sven (uidv7805)
simplify for plugin finder
- Added comments -  uidv7805 [Jul 14, 2015 9:32:40 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:24CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/val/project.pj
Revision 1.5 2015/03/06 12:46:50CET Mertens, Sven (uidv7805)
removing docu error
--- Added comments ---  uidv7805 [Mar 6, 2015 12:46:51 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.4 2014/10/13 11:42:03CEST Hecker, Robert (heckerr)
Corrected relative import usage.
--- Added comments ---  heckerr [Oct 13, 2014 11:42:03 AM CEST]
Change Package : 271307:1 http://mks-psad:7002/im/viewissue?selection=271307
Revision 1.3 2013/03/21 17:22:32CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:32 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.2 2013/02/19 14:07:32CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:32 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:59:37CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/db/val/project.pj
"""
