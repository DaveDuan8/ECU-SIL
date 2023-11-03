"""
framework.rep.__init__.py
-------------------

**Report generation package for different validation aspects and report formats.**


**User-API Interfaces**

  - `pdf`   packages for easy report generation
  - `Excel` package to create/update excel tables
  - `Word`  package to create MS Word files

**To generate a simple AlgoTestReport from your code do following:**

  .. code-block:: python

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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:22:09CET $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------
from . pdf.base.pdf import Pdf
from . pdf.algo_test.report import AlgoTestReport
from . import ifc
# from . pdf.reg_test.report import RegTestReport

# from . import report_base


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2020/03/25 21:22:09CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/project.pj
"""
