"""
framework/valf/obs/__init__.py
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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/04/02 15:07:53CEST $
"""


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.2 2020/04/02 15:07:53CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:39:24CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/obs/project.pj
"""
