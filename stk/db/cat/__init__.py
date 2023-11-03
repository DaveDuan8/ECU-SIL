"""
stk/db/cat/__init__.py
----------------------

This Subpackage provides a complete Interface CAT Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseRecCatalogDB`

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
test%5fdb/test%5fcat/project.pj&selection=test%5fcat.py

    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5fcat/project.pj&selection=test%5fcollection.py


**To use the cat package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.cat import BaseRecCatalogDB

    # Import error tolerance global constant
    from stk.db import ERROR_TOLERANCE_MED

    # Get a instance of Object DB interface.
    catdb = BaseRecCatalogDB(db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get collection record from database
    records = catdb.get_collections(12)

    # Terminate CAT database
    catdb.close()

    ...

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:37CEST $
"""
# Import STK Modules --------------------------------------------------------------------------------------------------
from stk.db.cat.cat import BaseRecCatalogDB  # base class providing common catalog interface methods
from stk.db.cat.cat import PATH_SEPARATOR
from stk.db.cat.cat import PluginRecCatalogDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.5 2016/08/16 12:26:37CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.4 2015/12/04 14:33:50CET Mertens, Sven (uidv7805)
removing a lint
Revision 1.3 2015/10/26 16:39:44CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
--- Added comments ---  uidv8815 [Oct 26, 2015 4:39:45 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.2 2015/07/14 09:29:05CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:29:06 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:03:56CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/cat/project.pj
Revision 1.5 2015/03/13 09:15:08CET Mertens, Sven (uidv7805)
docu fix
--- Added comments ---  uidv7805 [Mar 13, 2015 9:15:08 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.4 2014/12/08 08:40:15CET Mertens, Sven (uidv7805)
description update
--- Added comments ---  uidv7805 [Dec 8, 2014 8:40:15 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.3 2014/08/22 10:30:21CEST Ahmed, Zaheer (uidu7634)
Improve epy documentation
--- Added comments ---  uidu7634 [Aug 22, 2014 10:30:22 AM CEST]
Change Package : 245349:2 http://mks-psad:7002/im/viewissue?selection=245349
Revision 1.2 2013/03/21 17:22:35CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:36 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.1 2013/02/11 09:55:35CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/db/cat/project.pj
"""
