"""
stk/db/lbl/__init__.py
----------------------

This Subpackage provides a complete Interface ADMS_ADMIN schema to access Camera Label database.

**Following Classes are available for the User-API:**

  - `BaseCameraLabelDB`
  - `BaseGenLabelDB`
  - `RoadType`

**See also relevant Classes:**

  - `db_common`

**To get more information about the usage of the Object database interface, you can also check following Links:**

ADAS Database API Documentation.
    * This Document

Wiki Server with FAQ's
     * https://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation

Module test Code under
    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5flbl/project.pj&selection=test%5fcamlabel.py
    * http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools/\
Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/moduletest/\
test%5fdb/test%5flbl/project.pj&selection=test%5fgenlabel.py


**To use the lbl package from your code do following:**

  .. python::

    # Import db interface module
    from stk.db.lbl import BaseGenLabelDB

    # Import error tolerance global constant
    from stk.db.db_common import ERROR_TOLERANCE_MED

    # Get a instance of Object DB interface.
    genlbldb = BaseGenLabelDB(db_sqlite_path, error_tolerance=ERROR_TOLERANCE_MED)

    # Get Label attribute record from database
    attr = genlbldb.get_attributes(123):

    # Terminate Generic Label database
    genlbldb.close()

    ...

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:33CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------
from stk.db.lbl.genlabel import BaseGenLabelDB  # base class providing common catalog interface methods
from stk.db.lbl.camlabel import BaseCameraLabelDB
from stk.db.lbl.genlabel_defs import RoadType  # RoadType label definitions
from stk.db.lbl.camlabel import PluginCamLabelDB
from stk.db.lbl.genlabel import PluginGenLabelDB


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/08/16 12:26:33CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.3 2015/10/26 16:39:42CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
- Added comments -  uidv8815 [Oct 26, 2015 4:39:42 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.2 2015/07/14 09:30:50CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:30:51 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:04:08CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/lbl/project.pj
Revision 1.9 2014/11/17 08:33:13CET Mertens, Sven (uidv7805)
doku update
--- Added comments ---  uidv7805 [Nov 17, 2014 8:33:13 AM CET]
Change Package : 281272:1 http://mks-psad:7002/im/viewissue?selection=281272
Revision 1.8 2014/10/09 10:33:57CEST Mertens, Sven (uidv7805)
change imports to relatives
--- Added comments ---  uidv7805 [Oct 9, 2014 10:33:58 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.7 2014/10/06 16:01:15CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Oct 6, 2014 4:01:16 PM CEST]
Change Package : 245347:1 http://mks-psad:7002/im/viewissue?selection=245347
Revision 1.6 2014/10/06 15:43:04CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Oct 6, 2014 3:43:05 PM CEST]
Change Package : 245347:1 http://mks-psad:7002/im/viewissue?selection=245347
Revision 1.5 2013/05/14 10:35:58CEST Ibrouchene-EXT, Nassim (uidt5589)
Added import of road type definitions.
--- Added comments ---  uidt5589 [May 14, 2013 10:35:58 AM CEST]
Change Package : 182606:3 http://mks-psad:7002/im/viewissue?selection=182606
Revision 1.4 2013/03/21 17:22:33CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:34 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.3 2013/03/13 17:45:02CET Hecker, Robert (heckerr)
imported needed class.
--- Added comments ---  heckerr [Mar 13, 2013 5:45:02 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.2 2013/02/19 14:07:27CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:27 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:58:40CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/db/lbl/project.pj
"""
