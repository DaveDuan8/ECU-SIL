"""
stk/db/par/__init__.py
----------------------

This Subpackage provides a Interface to PAR Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseParDB`

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
test%5fdb/test%5fpar/project.pj&selection=test%5fpar.py


**To use the par package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.par import BaseParDB

    # Import error tolerance global constant
    from stk.db import ERROR_TOLERANCE_MED

    # Get a instance of Object DB interface.
    pardb = BaseParDB(db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get Confiuration Id
    config = pardb.get_config_id("MyconfigName")

    # Terminate PAR database
    pardb.close()

    ...

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:30CEST $
"""

# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------
from . par import BaseParDB  # base class providing common catalog interface methods
from stk.db.par.par import PluginParDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/08/16 12:26:30CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.3 2015/10/26 16:39:40CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
- Added comments -  uidv8815 [Oct 26, 2015 4:39:41 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.2 2015/07/14 09:31:41CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:31:41 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:17CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/par/project.pj
Revision 1.7 2014/10/13 11:39:05CEST Hecker, Robert (heckerr)
Corrected relative import usage.
--- Added comments ---  heckerr [Oct 13, 2014 11:39:06 AM CEST]
Change Package : 271307:1 http://mks-psad:7002/im/viewissue?selection=271307
Revision 1.6 2014/10/08 16:21:48CEST Mertens, Sven (uidv7805)
relative import replacement
--- Added comments ---  uidv7805 [Oct 8, 2014 4:21:49 PM CEST]
Change Package : 270174:1 http://mks-psad:7002/im/viewissue?selection=270174
Revision 1.5 2014/08/22 13:30:02CEST Ahmed, Zaheer (uidu7634)
improve Doc
--- Added comments ---  uidu7634 [Aug 22, 2014 1:30:02 PM CEST]
Change Package : 245349:3 http://mks-psad:7002/im/viewissue?selection=245349
Revision 1.4 2014/08/22 13:00:53CEST Ahmed, Zaheer (uidu7634)
Improved epy documentation
--- Added comments ---  uidu7634 [Aug 22, 2014 1:00:54 PM CEST]
Change Package : 245349:3 http://mks-psad:7002/im/viewissue?selection=245349
Revision 1.3 2013/03/21 17:22:32CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:32 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.2 2013/02/19 14:07:31CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:31 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:59:23CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/db/par/project.pj
"""
