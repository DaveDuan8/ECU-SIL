"""
stk/db/fct/__init__.py
----------------------

This Subpackage provides a complete Interface FCT Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseFctDB`

**See also relevant Classes:**

  - `db_common`

**To get more information about the usage of the Object database interface, you can also check following Links:**

ADAS Database API Documentation.
    * This Document

Enterprise Architecture design and document
     * http://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation/page/RQ%20Engineering%20for%20Tools

Wiki Server with FAQ's
     * https://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation

Module test Code under
    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5ffct/project.pj&selection=test%5ffct.py


**To use the fct package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.fct import BaseRecCatalogDB

    # Import error tolerance global constant
    from stk.db import ERROR_TOLERANCE_MED

    # Get a instance of Object DB interface.
    fctdb = BaseRecCatalogDB(db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get all stored scenarios from database
    scenarios = fctdb.get_all_scenarios()

    # Terminate fct database
    fctdb.close()

    ...


:org:           Continental AG
:author:        Sohaib Zafar

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:35CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------

from stk.db.fct.fct import BaseFctDB      # base class providing common catalog interface methods
from stk.db.fct.fct import PluginFctDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/08/16 12:26:35CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.3 2015/10/26 16:39:44CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
- Added comments -  uidv8815 [Oct 26, 2015 4:39:44 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.2 2015/07/14 09:29:46CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:29:46 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:00CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/fct/project.pj
Revision 1.3 2015/01/12 13:16:58CET Mertens, Sven (uidv7805)
removing deprecated method calls
--- Added comments ---  uidv7805 [Jan 12, 2015 1:16:58 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.2 2014/10/09 14:34:00CEST Zafar, Sohaib (uidu6396)
Documentation example epydoc
--- Added comments ---  uidu6396 [Oct 9, 2014 2:34:00 PM CEST]
Change Package : 245346:1 http://mks-psad:7002/im/viewissue?selection=245346
"""
