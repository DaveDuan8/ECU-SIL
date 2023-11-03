"""
stk/dmt/__init__.py
-------------------

Subpackage for Data Management.

This Subpackage provides Interfaces and functions to access data information of recordings stored on LIFS010.

**Following modules / classes are available for the User-API:**

  - `stk.dmt.lbl`  functions to access camera Label Db for orders, labelled sequences etc.,
                   check package `stk.db.lbl` how to access label object information

**To get more information about Labels and Label process you can also check following Links:**

Labelled Sections API Documentation.
    * This Document

Basic Label Information documents
     * on Function Test & Validation Sharepoint

Wiki Server with FAQ's
     * https://connext.conti.de/wikis/home?lang=de#!/wiki/ADAS%20Algo%20Validation

**To use the dmt package from your code do following:**

  .. python::

    # Import stk.dmt
    from stk import dmt

    # prepare bpl

    bpl_sects = dmt.lbl.merge_bpl_sequences(bpl_list, "MFC300", "sr", "eva", label_db)

    ...

See more examples in the function documentation.


:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/21 10:20:41CEST $
"""
# Import Python Modules -------------------------------------------------------

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------
from . import lbl
from ..mts import Bpl

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/21 10:20:41CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/dmt/project.pj
Revision 1.2 2014/07/17 18:28:45CEST Hospes, Gerd-Joachim (uidv8815) 
finalise epydoc
--- Added comments ---  uidv8815 [Jul 17, 2014 6:28:45 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.1 2014/07/15 19:32:22CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/dmt/project.pj
"""
