"""
framework/db/gbl/gbl_defs.py
----------------------

 Common definitions of the global tables

 Sub-Scheme GBL


:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:22:57CEST $
"""


# - classes -----------------------------------------------------------------------------------------------------------
class GblUnits(object):  # pylint: disable=R0903
    """
    Global Definition for list of units as stored in GBL_UNTS
    """
    UNIT_L_MM = "millimeter"
    UNIT_L_M = "meter"
    UNIT_L_KM = "kilometer"
    UNIT_L_US = "microsecond"
    UNIT_L_MS = "millisecond"
    UNIT_L_S = "second"
    UNIT_L_H = "hour"
    UNIT_L_MPS = "meters_per_second"
    UNIT_L_KMPH = "kilometers_per_hour"
    UNIT_L_DEG = "degree"
    UNIT_L_RAD = "radian"
    UNIT_L_MPS2 = "meters_per_second_squared"
    UNIT_L_DEGPS = "degrees_per_second"
    UNIT_L_RADPS = "radians_per_second"
    UNIT_L_CURVE = "curve"
    UNIT_L_NONE = "none"
    UNIT_L_BINARY = "binary"
    UNIT_L_PERCENTAGE = "percentage"
    UNIT_L_PER_H = "per_hour"
    UNIT_L_PER_KM = "per_kilometer"
    UNIT_L_PER_100KM = "per_100_kilometer"
    UNIT_M_KILOGRAM = "kilogram"
    UNIT_A_DECIBEL = "decibel"

    def __init__(self):
        pass


class GblTestType(object):  # pylint: disable=R0903
    """
    Global Definition to related to algorithm test report type
    as defined in database table GBL_TESTTYPE
    """
    TYPE_PERFORMANCE = "performance"
    TYPE_FUNCTIONAL = "functional"

    def __init__(self):
        pass


"""
CHANGE LOG:
-----------
$Log: gbl_defs.py  $
Revision 1.2 2020/03/31 09:22:57CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:24CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
