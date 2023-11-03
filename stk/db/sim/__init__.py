"""
stk/db/sim/__init__.py
----------------------

Classes for Database access of Simulation DB.

This Subpackage provides a complete Interface GBL Subschema for validation database.

**Following Classes are available for the User-API:**

  - `BaseSimulationDB`

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
test%5fdb/test%5fsim/project.pj&selection=test%5fsim.py


**To use the sim package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.sim import BaseSimulationDB

    # Get a instance of Object DB interface.
    simdb = BaseSimulationDB(db_sqlite_path)

    # Get sim file for record with given id from database
    id = simdb.get_sim_file(17)

    # Terminate sim database
    simdb.close()

    ...



:org:           Continental AG
:author:        Zaheer Ahmed

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:29CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------
from . sim import BaseSimulationDB  # base class providing common catalog interface methods
from stk.db.sim.sim import PluginSimDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.3 2016/08/16 12:26:29CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.2 2015/07/14 09:32:14CEST Mertens, Sven (uidv7805)
simplify for plugin finder
- Added comments -  uidv7805 [Jul 14, 2015 9:32:15 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:19CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/sim/project.pj
Revision 1.4 2015/01/19 16:13:57CET Mertens, Sven (uidv7805)
not really derived
--- Added comments ---  uidv7805 [Jan 19, 2015 4:13:58 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.3 2014/10/13 11:40:31CEST Hecker, Robert (heckerr)
Corrected relative import usage.
--- Added comments ---  heckerr [Oct 13, 2014 11:40:31 AM CEST]
Change Package : 271307:1 http://mks-psad:7002/im/viewissue?selection=271307
Revision 1.2 2014/10/08 16:21:48CEST Mertens, Sven (uidv7805)
relative import replacement
--- Added comments ---  uidv7805 [Oct 8, 2014 4:21:48 PM CEST]
Change Package : 270174:1 http://mks-psad:7002/im/viewissue?selection=270174
Revision 1.1 2014/07/04 10:29:55CEST Ahmed, Zaheer (uidu7634)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/db/sim/project.pj
"""
