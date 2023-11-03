"""
stk/db/gbl/__init__.py
----------------------

This Subpackage provides a complete Interface GBL Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseGblDB`

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
test%5fdb/test%5fgbl/project.pj&selection=test%5fgbl.py


**To use the gbl package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.gbl import BaseGblDB

    # Import error tolerance global constant
    from stk.db import ERROR_TOLERANCE_MED

    # Get a instance of Object DB interface.
    gbldb = BaseRecCatalogDB(db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get all projects from database
    projects = gbldb.get_all_project_name()

    # Terminate gbl database
    gbldb.close()

    ...

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:34CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------

from . gbl import BaseGblDB  # base class providing common interface methods
from . gbl_defs import GblUnits  # Global Unit class
from . gbl_defs import GblTestType  # Test types
from stk.db.gbl.gbl import PluginGblDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/08/16 12:26:34CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.3 2015/10/26 16:39:43CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
- Added comments -  uidv8815 [Oct 26, 2015 4:39:43 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.2 2015/07/14 09:30:12CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:30:13 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:03CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/gbl/project.pj
Revision 1.10 2015/01/19 16:13:14CET Mertens, Sven (uidv7805)
header
--- Added comments ---  uidv7805 [Jan 19, 2015 4:13:15 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.9 2014/10/13 11:35:11CEST Hecker, Robert (heckerr)
Corrected relative imports.
--- Added comments ---  heckerr [Oct 13, 2014 11:35:11 AM CEST]
Change Package : 271307:1 http://mks-psad:7002/im/viewissue?selection=271307
Revision 1.8 2014/10/08 16:21:50CEST Mertens, Sven (uidv7805)
relative import replacement
--- Added comments ---  uidv7805 [Oct 8, 2014 4:21:51 PM CEST]
Change Package : 270174:1 http://mks-psad:7002/im/viewissue?selection=270174
Revision 1.7 2014/07/14 14:56:01CEST Ahmed, Zaheer (uidu7634)
Improved eydoc and fixed pylint due to relative import
--- Added comments ---  uidu7634 [Jul 14, 2014 2:56:01 PM CEST]
Change Package : 245348:1 http://mks-psad:7002/im/viewissue?selection=245348
Revision 1.6 2014/06/26 21:22:24CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Jun 26, 2014 9:22:24 PM CEST]
Change Package : 242647:1 http://mks-psad:7002/im/viewissue?selection=242647
Revision 1.5 2014/06/19 12:21:07CEST Ahmed, Zaheer (uidu7634)
added Global definiation for testtype
--- Added comments ---  uidu7634 [Jun 19, 2014 12:21:07 PM CEST]
Change Package : 241731:1 http://mks-psad:7002/im/viewissue?selection=241731
Revision 1.4 2013/05/29 08:59:35CEST Raedler, Guenther (uidt9430)
- import GBLUntis definition
--- Added comments ---  uidt9430 [May 29, 2013 8:59:36 AM CEST]
Change Package : 180569:1 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.3 2013/03/21 17:22:34CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:34 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.2 2013/02/19 14:07:26CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:26 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:57:27CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/gbl/project.pj
"""
