"""
stk/mts/__init__.py
-------------------

Sub-package for Handle Tooling around MTS.

This sub-package provides some helper classes which are helpful around MTS.

**Following Classes are available for the User-API:**

  - `Rfe`       RecFileExtractor to get images out of a rec file
  - `Bpl`       BasePlayList to read/store/handle rec lists
  - `CdlUpdate` update project CDL directory out of MKS prj

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/04/15 17:37:41CEST $
"""
# Import Local Python Modules --------------------------------------------------
from bpl.bpl import Bpl
from bpl.bpl_base import BplList, BplListEntry
import cfg
from stk.mts.cfg_base import MtsConfig
from stk.mts.rfe import Rfe, RfeError
from stk.mts.rec import RecFileReader


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.3 2016/04/15 17:37:41CEST Hospes, Gerd-Joachim (uidv8815) 
pylint fixes
Revision 1.2 2015/10/09 16:50:06CEST Hospes, Gerd-Joachim (uidv8815)
pep8 pylint fixes
- Added comments -  uidv8815 [Oct 9, 2015 4:50:07 PM CEST]
Change Package : 381253:1 http://mks-psad:7002/im/viewissue?selection=381253
Revision 1.1 2015/04/23 19:04:36CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
Revision 1.17 2014/10/13 11:11:50CEST Mertens, Sven (uidv7805)
removing relative imports
--- Added comments ---  uidv7805 [Oct 13, 2014 11:11:51 AM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.16 2014/07/31 14:42:55CEST Hecker, Robert (heckerr)
Updated fro Backwardcompatibility.
--- Added comments ---  heckerr [Jul 31, 2014 2:42:55 PM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.15 2014/07/31 11:47:19CEST Hecker, Robert (heckerr)
changed import from sub-package.
--- Added comments ---  heckerr [Jul 31, 2014 11:47:19 AM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.14 2014/07/24 14:13:11CEST Hecker, Robert (heckerr)
Added RecFileReader as new "export"
--- Added comments ---  heckerr [Jul 24, 2014 2:13:12 PM CEST]
Change Package : 250811:1 http://mks-psad:7002/im/viewissue?selection=250811
Revision 1.13 2014/04/04 17:20:00CEST Hecker, Robert (heckerr)
Added Example to Rfe.
--- Added comments ---  heckerr [Apr 4, 2014 5:20:00 PM CEST]
Change Package : 227493:1 http://mks-psad:7002/im/viewissue?selection=227493
Revision 1.12 2014/03/03 09:30:23CET Hecker, Robert (heckerr)
Added rfe interface.
--- Added comments ---  heckerr [Mar 3, 2014 9:30:24 AM CET]
Change Package : 222649:1 http://mks-psad:7002/im/viewissue?selection=222649
Revision 1.11 2013/07/12 13:37:36CEST Hecker, Robert (heckerr)
Changed relative Import.
--- Added comments ---  heckerr [Jul 12, 2013 1:37:36 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.10 2013/07/12 13:23:26CEST Hecker, Robert (heckerr)
BugFix: get import working.
--- Added comments ---  heckerr [Jul 12, 2013 1:23:26 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.9 2013/06/27 16:03:42CEST Hecker, Robert (heckerr)
Added new module.
--- Added comments ---  heckerr [Jun 27, 2013 4:03:42 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.8 2013/06/26 17:19:02CEST Hecker, Robert (heckerr)
Some finetuning in docstrings and importing.
Revision 1.7 2013/06/26 16:02:39CEST Hecker, Robert (heckerr)
Reworked bpl sub-package.
Revision 1.6 2013/02/14 15:31:32CET Raedler, Guenther (uidt9430)
- added class to handle mts configurations (sorting)
--- Added comments ---  uidt9430 [Feb 14, 2013 3:31:32 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.5 2013/02/13 09:40:25CET Hecker, Robert (heckerr)
Adapted Package to new class Names.
--- Added comments ---  heckerr [Feb 13, 2013 9:40:25 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/01/23 07:56:33CET Hecker, Robert (heckerr)
Updated epydoc docu.
--- Added comments ---  heckerr [Jan 23, 2013 7:56:34 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2012/12/05 14:21:05CET Hecker, Robert (heckerr)
Removed stk Prefix
--- Added comments ---  heckerr [Dec 5, 2012 2:21:09 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 13:49:53CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:53 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 17:56:50CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
