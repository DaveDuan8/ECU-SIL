"""
stk/obj/field_of_view.py
-------------------

Field of view tester for labels according to L2 Spec chapter radar sensors

:org:           Continental AG
:author:        Miklos Sandor

"""

import math
import matplotlib.pyplot as plt
import numpy as np


class FieldOfView(object):
    """
    Tester methods for the FoV as specified in:
    L2_Req_Spec_ARS400/Device Requirements/Device Features/External Interfaces/Radar Interface/Field of View (FOV)
    Example usage:
    from stk.obj.field_of_view import FieldOfView

    fov = FieldOfView(FieldOfView.PREMIUM_SENSOR)
    if fov.is_point_in_fov(distx, disty):
        process(distx, disty)
    """

    ENTRY_SENSOR = 0
    PREMIUM_SENSOR = 1

    # entry consts
    EN_DIST_NEAR1 = 42.4
    EN_ANGLE_NEAR1 = math.radians(45)
    EN_X_NEAR1 = 30.0
    EN_X_NEAR2 = 69.8
    EN_X_FOCUS1 = 92.0
    EN_DIST_NEAR2 = 120.0
    EN_ANGLE_NEAR2 = math.radians(25.8)
    EN_ANGLE_FAR = math.radians(9)
    EN_DIST_FAR = 170
    EN_X_FOCUS2 = 391.7
    EN_ANGLE_END = math.radians(4)

    # premium consts
    PR_DIST_NEAR1 = 20.0
    PR_X_NEAR1 = 5.18
    PR_Y_NEAR1 = 19.3
    PR_X_FOCUS1 = 23.0
    PR_TAN_NEAR1 = PR_Y_NEAR1 / (PR_X_FOCUS1 + PR_X_NEAR1)
    PR_X_NEAR2 = 50.0
    PR_ANGLE_NEAR1 = math.radians(75)
    PR_DIST_NEAR2 = 70.0
    PR_ANGLE_NEAR2 = math.radians(45)
    PR_DIST_FAR = 250.0
    PR_ANGLE_FAR = math.radians(9)

    # is object detectable by the algo params
    OBJ_EGO_SPEED_THRESHOLD = 65 / 3.5  # m/s
    EDO_TARGET_DIST_THRESHOLD = 100  # m

    def __init__(self, sensor_type=PREMIUM_SENSOR):
        """
        :param: sensor_type: type of the radar sensor
        :type sensor_type: ENTRY_SENSOR, PREMIUM_SENSOR
        """
        self.filter_func = self.__is_obj_in_premium
        if sensor_type == FieldOfView.ENTRY_SENSOR:
            self.filter_func = self.__is_obj_in_entry

    def is_point_in_fov(self, distx, disty):
        """
        :param: distx: distance x / longitudinal distance
        :type distx: float
        :param: disty: distance y / latitudinal distance
        :type disty: float
        """
        return self.filter_func(distx, disty)

    @staticmethod
    def __is_obj_in_entry(distx, disty):
        """
        :param: distx: distance x / longitudinal distance
        :type distx: float
        :param: disty: distance y / latitudinal distance
        :type disty: float
        """
        x = float(distx)
        y = float(disty)
        dist = math.sqrt(pow(x, 2) + pow(y, 2))
        if x <= 0 or dist > FieldOfView.EN_DIST_FAR:
            return False
        elif dist > 0 and dist <= FieldOfView.EN_DIST_NEAR1:
            if math.fabs(y / x) < math.tan(FieldOfView.EN_ANGLE_NEAR1):
                return True
        elif x > FieldOfView.EN_X_NEAR1 and x <= FieldOfView.EN_X_NEAR2:
            if math.fabs(y / (FieldOfView.EN_X_FOCUS1 - x)) < math.tan(FieldOfView.EN_ANGLE_NEAR2):
                return True
        elif dist > FieldOfView.EN_X_NEAR2 and x <= FieldOfView.EN_DIST_NEAR2:
            if math.fabs(y / x) < math.tan(FieldOfView.EN_ANGLE_FAR):
                return True
        elif x > FieldOfView.EN_DIST_NEAR2 and dist <= FieldOfView.EN_DIST_FAR:
            if math.fabs(y / (FieldOfView.EN_X_FOCUS2 - x)) < math.tan(FieldOfView.EN_ANGLE_END):
                return True
        return False

    @staticmethod
    def __is_obj_in_premium(distx, disty):
        """
        :param: distx: distance x / longitudinal distance
        :type distx: float
        :param: disty: distance y / latitudinal distance
        :type disty: float
        """
        x = float(distx)
        y = float(disty)
        dist = math.sqrt(pow(x, 2) + pow(y, 2))
        if x <= 0 or dist > FieldOfView.PR_DIST_FAR:
            return False
        elif x > 0 and x <= FieldOfView.PR_X_NEAR1:
            if dist >= 0 and dist <= FieldOfView.PR_DIST_NEAR1:
                if math.fabs(y / x) < math.tan(FieldOfView.PR_ANGLE_NEAR1):
                    return True
        elif x > FieldOfView.PR_X_NEAR1 and x <= FieldOfView.PR_X_NEAR2:
            if math.fabs(y / (x + FieldOfView.PR_X_FOCUS1)) < FieldOfView.PR_TAN_NEAR1:
                return True
        elif dist > FieldOfView.PR_DIST_NEAR1 and dist <= FieldOfView.PR_DIST_NEAR2:
            if math.fabs(y / x) < math.tan(FieldOfView.PR_ANGLE_NEAR2):
                return True
        elif dist > FieldOfView.PR_DIST_NEAR2 and dist <= FieldOfView.PR_DIST_FAR:
            if math.fabs(y / x) < math.tan(FieldOfView.PR_ANGLE_FAR):
                return True
        return False

    def is_object_detectable(self, ego_speed, distx):
        """
        If the ego speed is lower than 65 kph, the detection distance is reduced by the algo to 100m,
        therefore do not count these cases

        :param: ego_speed:ego speed m/s
        :type ego_speed: float
        :param: distx: distance x m
        :type distx: float
        """
        if ego_speed is None or distx is None:
            return True
        if (distx < FieldOfView.EDO_TARGET_DIST_THRESHOLD or
           (distx >= FieldOfView.EDO_TARGET_DIST_THRESHOLD and ego_speed > FieldOfView.OBJ_EGO_SPEED_THRESHOLD)):
            return True
        return False

    @staticmethod
    def __debug_plot_gate(gate, x_min, x_max, y_min, y_max, step, colour):
        """
        debug plot for a specific tester/gate function

        :param: gate: tester function
        :param: x_min: x_min
        :param: x_max: x_max
        :param: y_min: y_min
        :param: step: step
        :param: colour: colour
        """
        for x in np.arange(x_min, x_max, step):
            for y in np.arange(y_min, y_max, step):
                if gate(x, y):
                    plt.plot(x, y, colour + '.')

    def debug_plot_all_gates(self):
        """
        plots both entry and premium beamform/FoV
        """
        x_min, x_max = -5, 255
        y_min, y_max = -130, 130
        step = 1

        # x_min, x_max = -5, 255
        # y_min, y_max = -50, 50
        # step = 1

        # plt.axis([-5, 255, -130, 130])
        plt.axis([x_min, x_max, y_min, y_max])
        plt.grid(True)
        colour = 'b'
        self.__debug_plot_gate(self.__is_obj_in_premium, x_min, x_max, y_min, y_max, step, colour)
        colour = 'g'
        self.__debug_plot_gate(self.__is_obj_in_entry, x_min, x_max, y_min, y_max, step, colour)

        plt.show()

"""
$Log: field_of_view.py  $
Revision 1.3 2015/12/14 14:39:21CET Hospes, Gerd-Joachim (uidv8815) 
pylint fixes
Revision 1.2 2015/12/14 09:51:22CET Hospes, Gerd-Joachim (uidv8815)
M.Sandor: STK OBJ DB labels are adjusted so that intervals are cut out,
where distx>100m and Vego<65kmh, similarily to the field of view implementation,
where intervals are cut out from labels, where the target car is out of the field of view.
Revision 1.1 2015/04/23 19:04:48CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.3 2014/11/06 14:28:03CET Mertens, Sven (uidv7805)
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:28:04 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.2 2014/10/17 15:35:21CEST Hecker, Robert (heckerr)
BugFix.
--- Added comments ---  heckerr [Oct 17, 2014 3:35:21 PM CEST]
Change Package : 273172:1 http://mks-psad:7002/im/viewissue?selection=273172
Revision 1.1 2014/09/26 13:00:40CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
"""
