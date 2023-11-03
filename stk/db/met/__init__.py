"""
stk/db/met/__init__.py
----------------------

This Subpackage provides a complete Interface MET (Meta Data) Subschema for validation database.

The table is only used by DataMining and StatusPage tools, no Valf usage is planned currently.

**Following Classes are available for the User-API:**

  - `BaseMetDB`

**See also relevant Classes:**

  - `DBConnect`

**To get more information about the usage of the Object database interface, you can also check following Links:**

ADAS Database API Documentation.
    * This Document

Enterprise Architecture design and document
     * http://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation/page/RQ%20Engineering%20for%20Tools

Wiki Server with FAQ's
     * https://connext.conti.de/wikis/home?lang=de#!/wiki/ADAS%20Algo%20Validation

Module test Code under
    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5fmet/project.pj&selection=test%5fmet.py


**To use the obj package from your code do following:**

  .. python::

    # Import db interface module
    from stk.db.met import met as dbmet

    # Import db connector
    from stk.db.db_connect import DBConnect

    # Import error tolerance global constant
    from stk.db.db_common import ERROR_TOLERANCE_MED

    # Create a instance of DB connector.
    db_connector = DBConnect(db_file=db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get a instance of Object DB interface.
    metdb = db_connector.connect(dbmet)

    # Initialize CAT database connection.
    metdb.initialze()

    # Terminate CAT database
    metdb.close()

    ...


:org:           Continental AG
:author:        Sohaib Zafar

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/09/27 15:50:51CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------

from stk.db.met.met import BaseMetDB      # base class providing common catalog interface methods


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/09/27 15:50:51CEST Hospes, Gerd-Joachim (uidv8815) 
rem unused import Plugin*
Revision 1.3 2016/09/27 15:39:26CEST Hospes, Gerd-Joachim (uidv8815)
doc and pylint fixes
Revision 1.2 2016/09/20 15:28:01CEST Zafar, Sohaib (uidu6396)
Init file
"""
