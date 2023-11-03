"""
framework/rep/__init__.py
-------------------

**Report generation package to create *.pdf reports.**


**User-API Interfaces**


`AlgoTestReport`
    class to build pdf reports with different templates/styles
    for performance, functional or regression tests


`base`
    package for developer defined reports providing only header and footer on page template

Pdf reports are created for a `stk.val.TestRun` stored in the Validation Result DB.

For testing purpose you can also use the interface class `ifc`
which provides the needed TestRun, TestCase and TestStep declarations.

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:23:04CET $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2020/03/25 21:23:04CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/project.pj
"""
