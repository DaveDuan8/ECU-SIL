"""
stk/db/cl/__init__.py
---------------------

Classes for Database access of Global Definitions.

Sub-Scheme GBL

This Subpackage provides a complete Interface CAT Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseCLDB`

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


**To use the cl package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.cl import BaseCLDB

    # Get a instance of Object DB interface.
    cldb = BaseCLDB(db_sqlite_path)

    # Get collection record from database
    constraints = cldb.get_constraint_set_ids()

    # Terminate CL database
    cldb.close()

    ...


:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:36CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------
from cl import BaseCLDB  # base class providing common catalog interface methods
from stk.db.cl.cl import PluginCLDB

# Import Local Python Modules -----------------------------------------------------------------------------------------


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.3 2016/08/16 12:26:36CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.2 2015/07/14 09:33:12CEST Mertens, Sven (uidv7805)
simplify for plugin finder
- Added comments -  uidv7805 [Jul 14, 2015 9:33:12 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:03:58CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/cl/project.pj
Revision 1.3 2013/12/06 13:08:17CET Hospes, Gerd-Joachim (uidv8815)
add cl db to db_connector for UseAllConnections
--- Added comments ---  uidv8815 [Dec 6, 2013 1:08:17 PM CET]
Change Package : 208339:1 http://mks-psad:7002/im/viewissue?selection=208339
Revision 1.2 2013/03/21 17:22:34CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:35 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.1 2013/02/21 12:39:42CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/db/cl/project.pj
"""
