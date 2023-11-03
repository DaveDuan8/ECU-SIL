"""
stk/valf/obs/__init__.py
------------------------

Subpackage for general observers running in ADAS Algo Validation Framework **ValF**.

This Subpackage provides observer classes based on `BaseComponentInterface` that are used by several projects
and supported by Validation Tools group.

**Following Observers are available for the User-API:**

  - `CollectionReader`
  - `BPLReader`, replaced by `CollectionReader`
  - `CATReader`, replaced by `CollectionReader`
  - `DBLinker`, successor of `DBConnector`
  - `SignalExtractor`
  - `TimeChecker`
  - `SODSACObserver`
  - `ResultSaver`

**Following Defines (classes/constants) are available for the User-API:**
  - `BaseComponentInterface`
  - `signal_defs`
  - `ValfError`

**Empty observer as template for new modules:**
  - `ExampleObserver`

**To get more information about the Validation support you can also check following Links:**

Valf API Documentation:
    * `Valf`

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/04/12 15:05:01CEST $
"""


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.2 2016/04/12 15:05:01CEST Hospes, Gerd-Joachim (uidv8815) 
fix docu during result saver implementation
Revision 1.1 2015/04/23 19:05:51CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
Revision 1.5 2015/02/10 19:39:39CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:41 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.4 2015/01/12 12:45:26CET Mertens, Sven (uidv7805)
committed some changes
--- Added comments ---  uidv7805 [Jan 12, 2015 12:45:27 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.3 2014/12/08 14:19:58CET Mertens, Sven (uidv7805)
update coll_reader according UncReplacer
Revision 1.2 2014/08/13 12:52:20CEST Hospes, Gerd-Joachim (uidv8815)
add sac_observer to description
--- Added comments ---  uidv8815 [Aug 13, 2014 12:52:20 PM CEST]
Change Package : 253112:1 http://mks-psad:7002/im/viewissue?selection=253112
Revision 1.1 2014/05/04 20:11:40CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
  04_Engineering/stk/valf/obs/project.pj
"""
