"""
stk/obj/ego.py
-------------------

Classes for ego motion handling

:org:           Continental AG
:author:        Nassim Ibrouchene

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:47CEST $
"""
# pylint: disable=E1101

import numpy as np

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.helper import deprecated

# --- Unit conversions ---
MPS2KPH = 3.6
KPH2MPS = 1.0 / 3.6


class EgoMotion(object):
    """
    A class for the ego path
    """
    DISTANCE_TO_COG = 2.75  # Distance from the sensor to the center of gravity.
    DEFAULT_SPEED_BINS = [0.0, 30.0, 60.0, 80.0, 100.0, 140.0, 180.0, 250.0]
    EGO_DISP_OLD = False

    def __init__(self, veh_speed, veh_accel, veh_yaw, time_stamps):
        """
        Constructor.

        :param veh_speed: the vehicle's speed.
        :param veh_accel: the vehicle's acceleration.
        :param veh_yaw: the vehicle's yaw rate.
        :param time_stamps: the MTS timestamps.
        """
        self.__cog_curvelength = None
        self.__cog_coordinates = None
        self.__ego_motion = None
        self.__timestamps = time_stamps
        self.__speed = veh_speed
        self.__accel = veh_accel
        self.__yaw = veh_yaw
        # --- Calculates the ego path related ---
        self.__set_ego_path()
        self.__set_ego_curve_length()

    def __set_ego_path(self):
        """
        Calculates the ego path.
        """
        # precalculations
        time = np.array(self.get_cycle_time())
        tsqrhalf = time * time * 0.5
        velocity = np.asarray(self.__speed)
        accel = np.asarray(self.__accel)
        psip = np.asarray(self.__yaw)
        psi = psip * time
        cos_psi = np.cos(psi)
        sin_psi = np.sin(psi)
        psisqr = psi * psi
        psicum = np.cumsum(psi)
        slip = 0
        cos_slip = np.cos(slip)
        sin_slip = np.sin(slip)
        dx_taylor_1 = -1.0 / 6.0
        dx_taylor_2 = 1.0 / 120.0
        dx_taylor_3 = -1.0 / 5040.0
        dx_taylor_4 = 1.0 / 362880.0
        dy_taylor_1 = 1.0 / 2.0
        dy_taylor_2 = -1.0 / 24.0
        dy_taylor_3 = 1.0 / 720.0
        dy_taylor_4 = -1.0 / 40320.0
        cs_cp = cos_slip * cos_psi
        ss_sp = sin_slip * sin_psi
        ss_cp = sin_slip * cos_psi
        cs_sp = cos_slip * sin_psi
        # delta_x = s * sin(psi)/psi
        # delta_y = s * (1-cos(psi)/psi)
        delta_s = accel * tsqrhalf + velocity * time
        delta_x = delta_s * (1 + (dx_taylor_1 + (dx_taylor_2 + (dx_taylor_3 + dx_taylor_4 * psisqr) * psisqr) * psisqr)
                             * psisqr)
        delta_y = delta_s * ((dy_taylor_1 + (dy_taylor_2 + (dy_taylor_3 + dy_taylor_4 * psisqr) * psisqr) * psisqr)
                             * psi)
        dx_abs = self.DISTANCE_TO_COG * (cos_psi - 1.0) - delta_x * (cs_cp + ss_sp) + delta_y * (ss_cp - cs_sp)
        dy_abs = -self.DISTANCE_TO_COG * sin_psi + delta_x * (cs_sp - ss_cp) - delta_y * (cs_cp + ss_sp)
        # prealocation
        # cumulative orientation angle sin/cos
        abs_dist = np.zeros(len(velocity))
        abs_angle = np.zeros(len(velocity))
        abs2rel_cos = np.zeros(len(velocity))
        abs2rel_sin = np.zeros(len(velocity))
        # cumaltive (x/y)-translation with VehicleSpeed type
        abs2rel_dx = np.zeros(len(velocity))
        abs2rel_dy = np.zeros(len(velocity))
        # cumulative driven distance
        cums = np.cumsum(delta_s)
        # set first elements
        abs_dist[0] = 0.0
        abs_angle[0] = 0.0
        abs2rel_cos[0] = 1.0
        abs2rel_sin[0] = 0.0
        # for cycle_idx = 2 : length(VehicleSpeed)  :
        for cycle_idx in xrange(1, len(velocity)):
            abs_dist[cycle_idx] = cums[cycle_idx - 1]
            abs_angle[cycle_idx] = psicum[cycle_idx - 1]
            abs2rel_cos[cycle_idx] = np.cos(psicum[cycle_idx - 1])
            abs2rel_sin[cycle_idx] = np.sin(psicum[cycle_idx - 1])
            abs2rel_dx[cycle_idx] = (cos_psi[cycle_idx - 1] * abs2rel_dx[cycle_idx - 1] + sin_psi[cycle_idx - 1] *
                                     abs2rel_dy[cycle_idx - 1] + dx_abs[cycle_idx - 1])
            abs2rel_dy[cycle_idx] = (-sin_psi[cycle_idx - 1] * abs2rel_dx[cycle_idx - 1] + cos_psi[cycle_idx - 1] *
                                     abs2rel_dy[cycle_idx - 1] + dy_abs[cycle_idx - 1])
        # inverse cumulative translation
        rel2abs_dx = abs2rel_sin * abs2rel_dy - abs2rel_dx * abs2rel_cos
        rel2abs_dy = -abs2rel_cos * abs2rel_dy - abs2rel_dx * abs2rel_sin
        # --- Set class attribute ---
        self.__cog_coordinates = np.array([list(rel2abs_dx), list(rel2abs_dy)])
        self.__ego_motion = np.array([np.array(list(rel2abs_dx)),
                                      np.array(list(rel2abs_dy)),
                                      np.array(list(abs2rel_dx)),
                                      np.array(list(abs2rel_dy)),
                                      np.array(list(abs_angle)),
                                      np.array(list(abs2rel_sin)),
                                      np.array(list(abs2rel_cos))])

    def __set_ego_curve_length(self):
        """
        Calculates the ego curve length.
        """
        delta_x = np.power(np.diff(self.__cog_coordinates[0, :]), 2)
        delta_y = np.power(np.diff(self.__cog_coordinates[1, :]), 2)
        temp = np.sqrt(delta_x + delta_y)
        self.__cog_curvelength = np.array([np.concatenate((([0]), np.cumsum(temp)))])

    def get_speed_in_kph(self):
        """
        Speed in kilometers per hour.

        :return: The speed in kilometers per hour.
        """
        return [s * MPS2KPH for s in self.__speed]

    def get_ego_displacement(self, start=None, end=None):
        """
        Calculate the ego displacement.

        :param start: Start index.
        :param end: End index.
        :return: displacement in meters
        :rtype:  float representing meters
        """
        if start is None and end is None:
            start = 0
            end = len(self.__speed)
        elif start is None:
            start = 0
        elif end is None:
            end = len(self.__speed)
        ego_displ = np.zeros((end - start))
        ego_displ[0] = 0.0
        for i in range(start + 1, end):
            delta_x = self.__cog_coordinates[0, i] - self.__cog_coordinates[0, i - 1]
            delta_y = self.__cog_coordinates[1, i] - self.__cog_coordinates[1, i - 1]
            ego_displ[i - start] = np.sqrt(np.power(delta_x, 2) + np.power(delta_y, 2))
        return ego_displ
        #================= old implementation =============================
        # ego_displ = [0] * len(self.__speed)
        # cycle_time = self.GetCycleTime()
        # if start is None and end is None:
        #    start = 0
        #    end = len(self.__speed)
        # elif start is None:
        #    start = 0
        # elif end is None:
        #    end = len(self.__speed)
        # for cycleidx in range(start, end):
        #    dt = cycle_time[cycleidx]
        #    ego_displ[cycleidx] = (self.__speed[cycleidx] * dt) + (0.5 * self.__accel[cycleidx] * math.pow(dt, 2))
        # return ego_displ
        #===================================================================

    def get_driven_distance(self, start=None, end=None):
        """
        Returns the driven distance between the provided indexes.

        :param start: Start index.
        :param end: End index.
        :return: distance in meters
        :rtype: float
        """
        if start is None and end is None:  # return the overall driven distance.
            return self.__cog_curvelength[0, -1]
        elif start is None:  # assume start from the beginning.
            return (self.__cog_curvelength[0, end] - self.__cog_curvelength[0, 0])
        elif end is None:  # assume end at the last index
            return (self.__cog_curvelength[0, -1] - self.__cog_curvelength[0, start])
        else:
            return (self.__cog_curvelength[0, end] - self.__cog_curvelength[0, start])

    def get_cycle_time_statistic(self):
        """
        Returns some statistics for the cycle time.

        :return: mean, std, min, max, total; all in seconds.
        :rtype: 5 floats
        """
        cycle_time_vec = self.get_cycle_time()
        mean_cycle_time = np.average(cycle_time_vec)
        std_cycle_time = np.std(cycle_time_vec)
        min_cycle_time = np.min(cycle_time_vec)
        max_cycle_time = np.max(cycle_time_vec)
        total_time = np.sum(cycle_time_vec)
        return mean_cycle_time, std_cycle_time, min_cycle_time, max_cycle_time, total_time

    def get_speed_statistic(self):
        """
        Returns some statistics for the speed.

        :return: mean, std, min, max; all in m/s
        :rtype:  4 floats representing meters per second.
        """
        mean_speed = np.average(self.__speed)
        std_speed = np.std(self.__speed)
        min_speed = np.min(self.__speed)
        max_speed = np.max(self.__speed)
        return mean_speed, std_speed, min_speed, max_speed

    def get_speed_histogram(self, speed, hist_bin=None, **kwargs):
        """
        Calculates a histogram of frames (counts) with speed using the specified bins.

        The function counts the values of speed matching a sequence in bins
        and returns a list with counted occurrences

        The returned units of the histogram (speed in [m/s] or [km/h]) depend on the input units.

        Example:

        .. python::

            # speed curve: accelerate to 100km/h, hold speed for 22 frames
            speed = range(0, 36) + [36] * 22 # in [m/s]
            # get num of frames/values with speed in provided bins (here: `DEFAULT_SPEED_BINS`)
            # as DEFAULT_SPEED_BINS units are [km/h] the speed has to be converted:
            speed_count_kph = self.egomot.get_speed_histogram([s * MPS2KPH for s in speed])
            # result: np.array [4  3  4  3  4  3  4  25]

        for a more detailed description of NumPy histograms see
        http://stackoverflow.com/questions/9141732/how-does-numpy-histogram-work

        for additional arguments find numpy.histogram reference at
        http://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html

        :param speed: list of speed values to be counted in the histogram
        :type speed:  list
        :param hist_bin: opt. binning for the histogram; default `DEFAULT_SPEED_BINS`
        :type hist_bin:  int or sequence of scalars
        :param kwargs: Keyword arguments for the numpy histogram function.

        :return: array of speed counts
        :rtype:  np.array
        """
        if hist_bin is None:
            hist_bin = self.DEFAULT_SPEED_BINS
        result = np.histogram(speed, hist_bin, **kwargs)
        return result[0]

    def get_time_speed_histogram(self, hist_bin=None, **kwargs):
        """
        Calculates a histogram of time driving with speed as specified in bins for the *ego path*

        The function summarises the times driven with speed matching a sequence in bins
        and returns an array with accumulated time values in hours.

        Unit for bins: km/h

        for a more detailed description of NumPy histograms see
        http://stackoverflow.com/questions/9141732/how-does-numpy-histogram-work

        for additional arguments find numpy.histogram reference at
        http://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html

        :param hist_bin: opt. binning for the histogram in [km/h]; default: `DEFAULT_SPEED_BINS`
        :type hist_bin:  int or sequence of scalars

        :return: arrays of times driven with given speeds
        :rtype:  np.array
        """
        if hist_bin is None:
            hist_bin = self.DEFAULT_SPEED_BINS

        cycle_times = [t / 3600 for t in self.get_cycle_time()]  # convert seconds to hours
        return np.histogram(self.get_speed_in_kph(), hist_bin, weights=cycle_times)[0]

    def get_dist_speed_histogram(self, hist_bin=None, **kwargs):
        """
        Calculates a histogram of distance driven with speed as specified in bins for the *ego path*

        The function sums up the distance driven with speed matching a sequence in bins
        and returns an array with accumulated distance values in km.

        Unit for bins: km/h

        for a more detailed description of NumPy histograms see
        http://stackoverflow.com/questions/9141732/how-does-numpy-histogram-work

        for additional arguments find numpy.histogram reference at
        http://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html

        :param hist_bin: opt. binning for the histogram in [km/h]; default `DEFAULT_SPEED_BINS`
        :type hist_bin:  int or sequence of scalars

        :return: array of distances driven with given speeds in [km]
        :rtype:  np.array
        """
        if hist_bin is None:
            hist_bin = self.DEFAULT_SPEED_BINS

        return np.histogram(self.get_speed_in_kph(), hist_bin,
                            weights=self.get_ego_displacement() * 1e-3)[0]

    def get_cycle_time(self):
        """
        Creates a cycle time vector using the MTS timestamps.

        :note: The first cycle is the same as the second one.
        :return: list of cycle times between timestamps; unit: seconds
        :rtype: list
        """
        length = len(self.__timestamps)
        cycle_time = [0] * length
        cycle_time[0] = float((self.__timestamps[1] - self.__timestamps[0])) / 1000000.0
        for i in xrange(1, length):
            cycle_time[i] = float((self.__timestamps[i] - self.__timestamps[i - 1])) / 1000000.0
        return cycle_time

    def get_ego_arc_length(self):
        """
        Returns the arc length vector

        :note unit: meters.
        """
        return self.__cog_curvelength

    def get_ego_motion_array(self):
        """
        Return the ego motion array

        :note: Array of size (7, nb_cycles) with rows correspond to

            - relative to absolute coordinates X
            - relative to absolute coordinates Y
            - absolute to relative coordinates X
            - absolute to relative coordinates Y
            - absolute angle
            - absolute to relative sine
            - absolute to relative cosine
        """
        return self.__ego_motion

    def get_ego_coordinates(self):
        """
        Returns the ego coordinates array

        :note The size of the array is (2, nb_cycles),
              the first line representing
              the X coordinates and the second the Y.
        """
        return self.__cog_coordinates

    @deprecated('__set_ego_path')
    def __SetEgoPath(self):  # pylint: disable=C0103
        """deprecated"""
        return self.__set_ego_path()

    @deprecated('__set_ego_curve_length')
    def __SetEgoCurveLength(self):  # pylint: disable=C0103
        """deprecated"""
        return self.__set_ego_curve_length()

    @deprecated('get_speed_in_kph')
    def GetSpeedInkph(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_speed_in_kph()

    @deprecated('get_ego_displacement')
    def GetEgoDisplacement(self, start=None, end=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_ego_displacement(start, end)

    @deprecated('get_driven_distance')
    def GetDrivenDistance(self, start=None, end=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_driven_distance(start, end)

    @deprecated('get_cycle_time_statistic')
    def GetCycleTimeStatistic(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_cycle_time_statistic()

    @deprecated('get_speed_statistic')
    def GetSpeedStatistic(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_speed_statistic()

    @deprecated('get_speed_histogram')
    def GetSpeedHistogram(self, speed, hist_bin=None, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.get_speed_histogram(speed, hist_bin, **kwargs)

    @deprecated('get_cycle_time')
    def GetCycleTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_cycle_time()

    @deprecated('get_ego_arc_length')
    def GetEgoArcLength(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_ego_arc_length()

    @deprecated('get_ego_motion_array')
    def GetEgoMotionArray(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_ego_motion_array()

    @deprecated('get_ego_coordinates')
    def GetEgoCoordinates(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_ego_coordinates()

"""
$Log: ego.py  $
Revision 1.1 2015/04/23 19:04:47CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.10 2015/02/06 16:46:29CET Ellero, Stefano (uidw8660) 
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:46:30 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.9 2015/01/22 14:29:23CET Ellero, Stefano (uidw8660) 
Removed all util based deprecated function usage inside stk and module tests.
Revision 1.8 2014/08/15 17:10:53CEST Hospes, Gerd-Joachim (uidv8815) 
new histogram for time/dist over speed
--- Added comments ---  uidv8815 [Aug 15, 2014 5:10:54 PM CEST]
Change Package : 253430:1 http://mks-psad:7002/im/viewissue?selection=253430
Revision 1.7 2014/06/24 09:42:16CEST Hospes, Gerd-Joachim (uidv8815)
test updated after naming convention fix, minor pylint fixes
--- Added comments ---  uidv8815 [Jun 24, 2014 9:42:16 AM CEST]
Change Package : 243818:1 http://mks-psad:7002/im/viewissue?selection=243818
Revision 1.6 2014/06/23 13:13:08CEST Baust, Philipp (uidg5548)
Changed signature to:  get_driven_distance(...
--- Added comments ---  uidg5548 [Jun 23, 2014 1:13:08 PM CEST]
Change Package : 243680:1 http://mks-psad:7002/im/viewissue?selection=243680
Revision 1.5 2014/06/16 12:59:37CEST Mertens, Sven (uidv7805)
correcting misspelled method name
--- Added comments ---  uidv7805 [Jun 16, 2014 12:59:38 PM CEST]
Change Package : 241722:1 http://mks-psad:7002/im/viewissue?selection=241722
Revision 1.4 2014/04/29 10:26:35CEST Hecker, Robert (heckerr)
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:35 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.3 2014/02/06 15:35:42CET Ibrouchene, Nassim (uidt5589)
Added notes precising the units used.
--- Added comments ---  uidt5589 [Feb 6, 2014 3:35:42 PM CET]
Change Package : 213484:1 http://mks-psad:7002/im/viewissue?selection=213484
Revision 1.2 2014/01/27 11:24:40CET Ibrouchene, Nassim (uidt5589)
Fixed a bug in the GetEgoDisplacement function.
--- Added comments ---  uidt5589 [Jan 27, 2014 11:24:41 AM CET]
Change Package : 213484:1 http://mks-psad:7002/im/viewissue?selection=213484
Revision 1.1 2013/05/14 10:29:07CEST Ibrouchene-EXT, Nassim (uidt5589)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
"""
