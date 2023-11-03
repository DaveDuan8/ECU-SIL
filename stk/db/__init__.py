r"""
stk/db/cat/__init__.py
----------------------

    Database connection package, providing sub-schemas and tables (see also `db_common`).

    ========= ====================   ==============================================================
     package   class                 usage
    ========= ====================   ==============================================================
     `cat`     `BaseRecCatalogDB`    recording (measurement) details and collections
     `cl`      `BaseCLDB`            constraint label tables as used in e.g. EBA
     `fct`     `BaseFctDB`           functional related recording details like scenarios,
                                     ego behaviour and criticality of events
     `gbl`     `BaseGblDB`           global definition tables like constants, units, db users
     `hpc`     `HpcErrorDB`          hpc errors as used by report generation
     `lbl`     `BaseGenLabelDB`      radar events with type and state
     `lbl`     `BaseCameraLabelDB`   additional label information in camera projects
     `met`     `BaseMetDB`           meta data stored and used only by data mining and status page
     `obj`     `BaseObjDataDB`       object detection results and calculation
     `sim`     `BaseSimulationDB`    camera and radar sensor fusion
     `val`     `BaseValResDB`        validation results stored for assessment,
                                     reports and doors export
    ========= ====================   ==============================================================

    **usage**:

    Example of instance:

    Parameters to any sub class of BaseDB described below.
    Sub classes are e.g. BaseRecCatalogDB or BaseGblDB

    when instantiating you can create a DB connection via old DBConnect
    or just use the new simplicity, e.g. "MFC4xx" or "ARS4XX" to connect
    to Oracle or "D:\data\myown.sqlite" to connect to your own sqlite file
    or "D:\data\label.sdf" to connect to your label DB.
    That's it!

    **Example**:

    .. python::

      db = BaseGblDB('ARS4XX', error_tolerance=ERROR_TOLERANCE_INFO)
      db.execute_some_command(some, args)
      db.close()

      # or with one less line:
      with BaseGblDB('ARS4XX', error_tolerance=ERROR_TOLERANCE_INFO) as db:
        db.some_command(some, args)

      ...


:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/09/27 15:40:39CEST $
"""
# - imports -----------------------------------------------------------------------------------------------------------

import db_sql as sql
import db_common as common
from db_common import AdasDBError
from db_common import ERROR_TOLERANCE_LOW
from db_common import ERROR_TOLERANCE_NONE
from db_common import ERROR_TOLERANCE_MED
from db_common import ERROR_TOLERANCE_HIGH
import db_connect as connect

from . import cat
from . import gbl
from . import fct
from . import obj
from . import par
from . import val
from . import lbl
from . import mdl
from . import met

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.5 2016/09/27 15:40:39CEST Hospes, Gerd-Joachim (uidv8815) 
adding met db
Revision 1.4 2016/08/16 16:01:45CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.3 2016/08/16 15:04:39CEST Hospes, Gerd-Joachim (uidv8815)
update docu
Revision 1.2 2015/07/17 17:57:48CEST Hospes, Gerd-Joachim (uidv8815)
fix comment
- Added comments -  uidv8815 [Jul 17, 2015 5:57:49 PM CEST]
Change Package : 353993:1 http://mks-psad:7002/im/viewissue?selection=353993
Revision 1.1 2015/04/23 19:03:51CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/db/project.pj
Revision 1.13 2015/03/13 09:07:00CET Mertens, Sven (uidv7805)
intendation fix
--- Added comments ---  uidv7805 [Mar 13, 2015 9:07:01 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.12 2015/03/05 14:58:59CET Mertens, Sven (uidv7805)
underline missing
--- Added comments ---  uidv7805 [Mar 5, 2015 2:59:00 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.11 2014/12/08 08:49:29CET Mertens, Sven (uidv7805)
update description according to CR
Revision 1.10 2014/10/08 16:21:47CEST Mertens, Sven (uidv7805)
relative import replacement
--- Added comments ---  uidv7805 [Oct 8, 2014 4:21:47 PM CEST]
Change Package : 270174:1 http://mks-psad:7002/im/viewissue?selection=270174
Revision 1.9 2013/11/28 13:56:19CET Zafar-EXT, Sohaib (uidu6396)
import fct
--- Added comments ---  uidu6396 [Nov 28, 2013 1:56:19 PM CET]
Change Package : 208164:1 http://mks-psad:7002/im/viewissue?selection=208164
Revision 1.7 2013/03/15 17:23:11CET Hecker, Robert (heckerr)
Undo some modification to get unittests working.
--- Added comments ---  heckerr [Mar 15, 2013 5:23:12 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.6 2013/03/15 17:05:18CET Hecker, Robert (heckerr)
Removed some pylint messages.
--- Added comments ---  heckerr [Mar 15, 2013 5:05:19 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.5 2013/02/27 13:59:45CET Hecker, Robert (heckerr)
Some changes regarding Pep8
--- Added comments ---  heckerr [Feb 27, 2013 1:59:46 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/26 16:19:54CET Raedler, Guenther (uidt9430)
- publish exception handler and global var from db_common
--- Added comments ---  uidt9430 [Feb 26, 2013 4:19:55 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/19 14:09:06CET Raedler, Guenther (uidt9430)
- use common db connector class
--- Added comments ---  uidt9430 [Feb 19, 2013 2:09:07 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/11 10:02:01CET Raedler, Guenther (uidt9430)
added sub packages for cat / gbl / lbl / obj / par / val sub-schemes
--- Added comments ---  uidt9430 [Feb 11, 2013 10:02:01 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/01/23 07:59:37CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/stk/db/project.pj
"""
