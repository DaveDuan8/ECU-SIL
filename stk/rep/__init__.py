"""
stk.rep.__init__.py
-------------------

**Report generation package for different validation aspects and report formats.**

.. packagetree::
   :style: UML

**User-API Interfaces**

  - `pdf`   packages for easy report generation
  - `Excel` package to create/update excel tables
  - `Word`  package to create MS Word files

**To generate a simple AlgoTestReport from your code do following:**

  .. python::

    # Import stk.rep
    import stk.rep as rep

    # Create a instance of the reporter class.
    report = rep.AlgoTestReport()

    # Create a Testrun Object
    testrun = rep.TestRun()

    # Fill in Data into the TestRun
    ...

    # Add one ore multiple Testcases into the report
    report.set_test_run(testrun)

    # Save the Report to Disk
    report.build("AlgoTestReport.pdf")

    ...


:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:58CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------
from . pdf.base.pdf import Pdf
from . pdf.algo_test.report import AlgoTestReport
from . pdf.fct_test.report import FctTestReport
from . import ifc
from . pdf.reg_test.report import RegTestReport

from . import report_base

import reportlab.platypus.flowables
import reportlab.lib.units

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:04:58CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.15 2015/02/10 19:39:41CET Hospes, Gerd-Joachim (uidv8815) 
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:43 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.14 2014/06/05 16:24:18CEST Hospes, Gerd-Joachim (uidv8815) 
final fixes after approval from Zhang Luo: cleanup and epydoc, pylint and pep8
--- Added comments ---  uidv8815 [Jun 5, 2014 4:24:19 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.13 2014/06/03 18:17:12CEST Hospes, Gerd-Joachim (uidv8815)
add fct_test class
--- Added comments ---  uidv8815 [Jun 3, 2014 6:17:13 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.12 2014/04/04 17:40:30CEST Hospes, Gerd-Joachim (uidv8815)
add reg_test
--- Added comments ---  uidv8815 [Apr 4, 2014 5:40:30 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.11 2013/10/25 09:02:28CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:29 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.10 2013/10/24 17:39:00CEST Hecker, Robert (heckerr)
to get unittest working again.
--- Added comments ---  heckerr [Oct 24, 2013 5:39:01 PM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.9 2013/10/21 08:41:20CEST Hecker, Robert (heckerr)
updated doxygen description.
--- Added comments ---  heckerr [Oct 21, 2013 8:41:20 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.8 2013/10/18 09:34:28CEST Hecker, Robert (heckerr)
Changed to new AlgoTestReporter Class.
--- Added comments ---  heckerr [Oct 18, 2013 9:34:28 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
"""
