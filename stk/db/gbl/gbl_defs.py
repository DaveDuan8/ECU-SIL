"""
stk/db/gbl/gbl_defs.py
----------------------

 Common definitions of the global tables

 Sub-Scheme GBL


:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:39CEST $
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
Revision 1.2 2016/08/16 16:01:39CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.1 2015/04/23 19:04:03CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/db/gbl/project.pj
Revision 1.8 2015/03/10 11:30:34CET Mertens, Sven (uidv7805)
removing errors
--- Added comments ---  uidv7805 [Mar 10, 2015 11:30:34 AM CET]
Change Package : 314142:2 http://mks-psad:7002/im/viewissue?selection=314142
"""
