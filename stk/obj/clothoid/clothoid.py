"""
stk/obj/clothoid/clothoid.py
-------------------

Classes for Clothoid Object Handling

:org:           Continental AG
:author:        Nassim Ibrouchene

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/10/08 17:21:28CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
# from warnings import warn
from math import ceil
from threading import Thread
from matplotlib.lines import Line2D
import numpy as np

# - import STK modules ------------------------------------------------------------------------------------------------
# import stk.val as val_res
import stk.obj.geo.point as val_pt
import stk.img as val_plot
import stk.util.logger as util_log
# import stk.util.helper as val_helper
from stk.val.base_events import ValBaseEvent, ValEventError
# import stk.db.lbl.genlabel_defs as lbl_defs
import stk.db.lbl as stk_lbl
from stk.util.helper import deprecated

# - defines -----------------------------------------------------------------------------------------------------------
ROAD_PATH = np.arange(0, 211)
SQRT_PATH = np.power(ROAD_PATH, 2)
ROAD_ONES = np.ones(211)
RDTYPE_DEFS = stk_lbl.RoadType()
EVENT_ATTR_EVENT_IMAGE = "clothoideventimage"


# - helper functions --------------------------------------------------------------------------------------------------
def getroadtrajestimationerror(clothoid, transformation_matrix, ego_cog, cycle_index, eval_samples):
    """
    Calculates the error made in estimating a trajectory
    using the clothoid model.

    :param clothoid: The model parameters (c0, c1, m).
    :param transformation_matrix: the list of transformation's matrix parameters [cos,sin,dx,dy].
    :param ego_cog: the center of gravity coordinates of the ego vehicle.
    :param cycle_index: the current cycle index.
    :param eval_samples: The samples (distances) for which the estimation error is calculated.
    """
    estimation_error = []
    cloth = getestimation(clothoid)
    estimation_abs = np.zeros((2, np.shape(cloth)[0]))
    estimation_abs[0, ] = (transformation_matrix[0] * ROAD_PATH -
                           transformation_matrix[1] * cloth +
                           transformation_matrix[2] * ROAD_ONES)
    estimation_abs[1, ] = (transformation_matrix[1] * ROAD_PATH +
                           transformation_matrix[0] * cloth +
                           transformation_matrix[3] * ROAD_ONES)
    estimate_arc_length = np.concatenate((([0]), np.cumsum(np.sqrt(np.power(np.diff(estimation_abs[0, ]), 2) +
                                                                   np.power(np.diff(estimation_abs[1, ]), 2)))))
    ego_arc_length = np.concatenate((([0]), np.cumsum(np.sqrt(np.power(np.diff(ego_cog[0:1, cycle_index:]), 2) +
                                                              np.power(np.diff(ego_cog[1:2, cycle_index:]), 2)))))

    estimation = getsamplesbyarclength(estimation_abs[0:2, :], estimate_arc_length, eval_samples)
    ground_truth = getsamplesbyarclength(ego_cog[0:2, cycle_index:], ego_arc_length, eval_samples)
    for i in range(0, np.shape(ground_truth[0])[0]):
        gt_x = (ground_truth[0])[i] - (ground_truth[0])[i - 1]
        gt_y = (ground_truth[1])[i] - (ground_truth[1])[i - 1]
        dx = (ground_truth[0])[i] - (estimation[0])[i]
        dy = (ground_truth[1])[i] - (estimation[1])[i]
        estimation_error.append(np.sign(dx * gt_y - dy * gt_x) * np.sqrt(dx ** 2 + dy ** 2))

    return estimation_error


def getestimation(clothoid):
    """ Returns the estimated road.

    :param clothoid: The model parameters (c0, c1, m).
    :return: Estimated road.
    """
    klothoid = (np.dot(clothoid[1] / 6, np.multiply(ROAD_PATH, SQRT_PATH)) + np.dot(clothoid[0] / 2, SQRT_PATH) +
                np.dot(clothoid[2], ROAD_PATH))
    return klothoid


def getsamplesbyarclength(curve_samples, curve_arc_length, arc_length_samples):
    """
    Gets samples coordinates by arc length.

    @param curve_samples: raw samples.
    @param curve_arc_length: arc length of curve_samples.
    @param arc_length_samples: Distances at which we want to retrieve the samples from curve_samples.
    @return X,Y: x,y coordinates of the samples at ArclengthSamples distance, taken out from curve_samples.
    """
    idx = []
    distances = list(arc_length_samples)
    for dist in distances:
        idx.append(np.abs(curve_arc_length - dist).argmin())
    idx_shifted = [x - 1 for x in idx]
    inter_sample_dist = ((arc_length_samples - curve_arc_length[idx_shifted]) /
                         (curve_arc_length[idx] - curve_arc_length[idx_shifted]))
    x = curve_samples[0, idx_shifted] + inter_sample_dist * (curve_samples[0, idx] - curve_samples[0, idx_shifted])
    y = curve_samples[1, idx_shifted] + inter_sample_dist * (curve_samples[1, idx] - curve_samples[1, idx_shifted])
    return x, y


class ClothoidEstimation(object):
    """ A class for the clothoid estimation """
    MAX_PARALLEL_THREADS = 20

    def __init__(self, c0, c1, yaw, ego_motion, veh_speed):
        """ Class constructor """
        self.__logger = util_log.Logger(self.__class__.__name__)
        self.__c0 = c0
        self.__c1 = c1
        self.__yaw = yaw
        self.__ego_motion = ego_motion
        self.__veh_speed = veh_speed
        self.estimation_error = None

    def calculate_estimation_error(self, last_usable_cycle, cog_coordinates,
                                   evaluation_samples, time_evaluation=True, indexes=None):
        """
        Calculates the estimation error for every usable cycle using the
        provided evaluation samples.

        :param last_usable_cycle: The last usable cycle.
        :param cog_coordinates: The center of gravity's coordinates.
        :param evaluation_samples: The samples for which the clothoid estimation is evaluated.
        :param time_evaluation: Boolean. True if the evaluation samples are time based,
                                false if they are distance based.
        """
        self.estimation_error = np.zeros((len(evaluation_samples), last_usable_cycle))
        # Multi-threading
        # --- Determine how many threads should be generated ---
        nb_threads = self.__GetNumberofThreads()
        cycles = list(np.arange(0, last_usable_cycle, int(last_usable_cycle / nb_threads)))
        cycles.append(last_usable_cycle)
        # --- Constructing the threads ---
        threads = []
        for index in range(1, len(cycles)):
            threads.append(MultiThreading(index, "Thread-" + "%d" % index,
                                          cog_coordinates,
                                          self.__c0,
                                          self.__c1,
                                          self.__yaw,
                                          self.__ego_motion,
                                          self.__veh_speed,
                                          cycles[index - 1],
                                          cycles[index],
                                          self.estimation_error,
                                          evaluation_samples,
                                          time_evaluation,
                                          indexes))
        # --- Executing the threads ---
        monitoring = []
        for thread in threads:
            thread.start()
            monitoring.append(thread)

        self.__logger.info("%d Threads are running for this file" % nb_threads)
        for thread in monitoring:
            thread.join()
        self.__logger.info("%d Threads finished running" % nb_threads)

    def __get_number_of_threads(self):
        """
        Determines the number of threads to use

        :return: the number of threads """
        total_nb_cycles = len(self.__c0)
        nb_threads = ceil(float(total_nb_cycles) / 8000.0)
        nb_threads = np.minimum(nb_threads, self.MAX_PARALLEL_THREADS)

        return nb_threads

    def get_estimation_error(self):
        """ Returns the time based estimation error
        """
        return self.estimation_error

    @deprecated('calculate_estimation_error')
    def CalculateEstimationError(self, last_usable_cycle, cog_coordinates,
                                 evaluation_samples, time_evaluation=True):
        """deprecated"""
        return self.calculate_estimation_error(last_usable_cycle,
                                               cog_coordinates,
                                               evaluation_samples,
                                               time_evaluation)

    @deprecated('get_estimation_error')
    def GetEstimationError(self):
        """deprecated"""
        return self.get_estimation_error()

    def __GetNumberofThreads(self):

        return self.__get_number_of_threads()


class Clothoid(object):
    """
    A class to handle the clothoid events
    """
    CLOTHOID_PLOT_KEYWORD = "clothoideventplot"

    def __init__(self, eventtype, event_threshold, estimation_error,
                 timestamps, event_sample, time_based_sample=True):
        """ Constructor for the class
        :param eventtype: The event type.
        :param event_threshold: The threshold (in m) used to trigger an event.
        :param estimation_error: The clothoid estimation error vector.
        :param timestamps: The timestamp vector.
        :param event_sample: The evaluation sample used for event generation.
        :param time_based_sample: Boolean. True if the evaluation samples are time based,
                                  false if they are distance based.
        """
        self.__logger = util_log.Logger(self.__class__.__name__)
        self.__eventtype = eventtype
        self.__threshold = event_threshold
        self.__eventsample = event_sample
        self.__time_based_sample = time_based_sample
        self.__estimation_error = estimation_error
        self.__timestamp = timestamps
        self.__event_list = None
        self.__event_signal = None

    def detect_and_filter_events(self, grouping_pattern=None, bool_indexes=None,
                                 label_signal=None, min_duration=None):
        """
        Detects events for the clothoid estimation and filters them

        :param grouping_pattern: a pattern used to group events that are close to each other.
        :param bool_indexes: An array containing booleans for specific index processing.
        :param label_signal: The road type label signal.
        :param min_duration: Minimal duration in cycles for an event to be taken into consideration.
        """
        self.__detect_threshold_exceed()
        if bool_indexes is not None:
            self.__ProcessSpecialIndexes(bool_indexes)
        if grouping_pattern is not None:
            self.__group_clothoid_events(grouping_pattern)
        if label_signal is not None:
            self.__filter_events_per_road_type(label_signal)
        if min_duration is not None:
            self.__filter_events_by_duration(min_duration)

    def __detect_threshold_exceed(self):
        """ Detects events in the estimation error array and sets the event signal attribute.
        """
        # --- Event signal is initialized with zeros ---
        self.__event_signal = np.zeros(np.shape(self.__estimation_error)[0])
        # --- Event signal is equal to one when the error is over the threshold ---
        self.__event_signal[np.nonzero(self.__estimation_error >= self.__threshold)] = 1

    def __process_special_indexes(self, boolean_indexes):
        """ Sets the event signal to zero in the specified indexes.
        :param boolean_indexes: An array with the same size as the event signal. Events set to zero where False.
        """
        self.__event_signal[np.logical_not(boolean_indexes)] = 0

    def __group_clothoid_events(self, pattern):
        """ Filters the events and creates the event list.
        :param pattern: The pattern for event grouping.
        """
        # --- Convolve event_signal with pattern ---
        convolution = np.convolve(self.__event_signal, pattern)
        # --- Clip values to 0 and 1 ---
        clipped_convolution = np.clip(convolution, 0, 1)
        # --- Get index list ---
        edges = np.convolve(clipped_convolution, [1, -1])
        indexes = np.nonzero(edges)

        idx = list(indexes[0])
        self.__event_list = []
        # --- If len idx is zero then there are no events , also len idx has to be a multiple of 2 ---
        if len(idx) > 0 and not (len(idx) % 2):
            i = 0
            while i < len(idx):
                start = idx[i]
                # --- The convolution shifts the end of the events of (len(smoother) - 1) ---
                stop = idx[i + 1] - (len(pattern) - 1)
                # --- Create new clothoid base event ---
                ev = ValClothoidEvent(self.__timestamp[start], start,
                                      self.__timestamp[stop], stop,
                                      self.__eventtype)
                ev.set_event_threshold(self.__threshold)
                ev.set_estimation_error(self.__estimation_error[ev.get_start_index()])
                ev.set_time_sample(self.__eventsample)
                self.__event_list.append(ev)
                i += 2

    def __filter_events_per_road_type(self, label_signal):
        """ Filters the event per road type, i.e keeps events happening in the same road type.
        :param label_signal: The road type label signal
        """
        filtered_events = []
        for ev in self.__event_list:
            rdtype = label_signal[ev.get_start_index():ev.GetStopIndex()]
            # --- Calculate diff, and if sum diff is null then road type is the same during the entire event ---
            if np.sum(np.diff(rdtype)) == 0:
                ev.set_road_type(rdtype[0])
                filtered_events.append(ev)
        self.__event_list = filtered_events

    def __filter_events_by_duration(self, nb_cycle_min=None):
        """ Filters the event against a minimal cycle amount.
        :param nb_cycle_min: The minimal cycle number for an event to be kept.
        """
        if nb_cycle_min is not None:
            filtered_events = []
            for ev in self.__event_list:
                if ev.GetEventCycles() >= nb_cycle_min:
                    filtered_events.append(ev)
            self.__event_list = filtered_events

    def set_clothoid_parameters(self, c0, c1, yaw, timing=False):
        """ For every event sets the clothoid parameters in the event attributes.
        :param c0, c1, yaw: the clothoid parameters.
        """
        for ev in self.__event_list:
            ev.set_clothoid_params(c0, c1, yaw, timing=timing)

    def set_ego_kinematics(self, vdy_data, timing=False):
        """ Sets the ego kinematics for the events.
        :param vdy_data: the vdy data container.
        """
        filtered_events = []
        for ev in self.__event_list:
            if np.all(np.array(vdy_data["VehicleSpeed"][ev.get_start_index():ev.GetStopIndex()]) > 0.0):
                ev.set_ego_kinematics(vdy_data, timing=timing)
                filtered_events.append(ev)
        self.__event_list = filtered_events

    def get_clothoid_event_list(self):
        """ Return the clothoid event list """
        return self.__event_list

    def generate_clothoid_plot(self, c0, c1, yaw, speed, ego_motion, cog_arclength, output):
        """ Generates a plot for the clothoid events.
        :param c0, c1, yaw: The clothoid parameters.
        :param speed: Vehicle speed.
        :param ego_motion: Ego motion.
        :param cog_arclength: The ego car's arc length.
        :param output: the output path folder.
        """
        cog_coordinates = ego_motion[0:2].copy()
        plotter = val_plot.ValidationPlot(output)
        for ev in self.__event_list:
            # --- Get the start index and the index corresponding to a travelled distance of 200m ---
            try:
                start = ev.get_start_index()
                stop = np.nonzero(cog_arclength[0, ] >= (cog_arclength[0, start] + 200.0))[0][0]
            except ValueError as ex:
                self.__logger.warning("Could not generate event image because of %s" % ex)
            else:
                # --- Create an empty figure ---
                ax = plotter.generate_figure()
                plot_data = []
                legend = []
                # --- Ego vehicle's path ---
                cog_x = cog_coordinates[0, start:stop]
                cog_y = cog_coordinates[1, start:stop]
                cog_z = np.ones(cog_x.size)
                cog_event = np.array([cog_x, cog_y, cog_z])
                cog_alength = np.concatenate((([0]), np.cumsum(np.sqrt(np.power(np.diff(cog_event[0:1]), 2) +
                                                                       np.power(np.diff(cog_event[1:2]), 2)))))
                # --- Switch back to car coordinates ---
                transfo_matrix = np.array([[ego_motion[6][start], ego_motion[5][start], ego_motion[2][start]],
                                           [-ego_motion[5][start], ego_motion[6][start], ego_motion[3][start]],
                                           [0, 0, 1]])
                cog_transformed = np.dot(transfo_matrix, cog_event)
                plot_data.append(val_pt.get_point_pair_list(list(cog_transformed[1, ]), list(cog_transformed[0, ])))
                legend.append("Ego vehicle's path")
                # --- Plot clothoid ---
                clt_x = np.arange(0, 200, 0.1)
                clt_y = (yaw[start] * clt_x +
                         (c0[start] / 2.0) * clt_x ** 2 +
                         (c1[start] / 6.0) * clt_x * clt_x ** 2)
                clt_event = np.array([clt_x, clt_y])
                clt_alength = np.concatenate((([0]), np.cumsum(np.sqrt(np.power(np.diff(clt_event[0:1]), 2) +
                                                                       np.power(np.diff(clt_event[1:2]), 2)))))
                plot_data.append(val_pt.get_point_pair_list(list(clt_y), list(clt_x)))
                legend.append("Road course estimation")
                # --- Generate plot ---
                img = plotter.generate_plot(plot_data, legend, "error e(m)", "P(error > e)", True, True,
                                            title="Event visualization", axes=ax, line_colors=['0.75', 'r'],
                                            line_width=[4.0, 2.0])
                # --- Get comparison points ---
                try:
                    if self.__time_based_sample is True:
                        distance = self.__eventsample * speed[start]
                    else:
                        distance = self.__eventsample
                    cog_cmp_idx = np.nonzero(cog_alength <= distance)[0][-1]
                    clt_cmp_idx = np.nonzero(clt_alength >= distance)[0][0]
                    x1 = clt_x[clt_cmp_idx]
                    y1 = clt_y[clt_cmp_idx]
                    x2 = cog_transformed[0, ][cog_cmp_idx]
                    y2 = cog_transformed[1, ][cog_cmp_idx]
                    line = Line2D([y1, y2], [x1, x2], color='g', ls='-', linewidth=2.0)
                    ax.add_line(line)
                    ax.text(0.01, 0.9, "|err| = %0.2fm" % ev.get_estimation_error(), transform=ax.transAxes)
                except ValueError as ex:
                    self.__logger.warning("No line could be drawn between the comparion points %s" % ex)
                finally:
                    # --- Set plot parameters ---
                    img.xlim([-40, 40])
                    img.xlabel("Y axis")
                    img.ylim([0, 200])
                    img.ylabel("X axis")
                    img.gca().invert_xaxis()
                    try:
                        img_buffer = plotter.get_plot_data_buffer(img)
                    except Exception as ex:
                        self.__logger.error("Could not save event image %s" % ex)
                    else:
                        ev.set_event_image(img_buffer)

    @deprecated('detect_and_filter_events')
    def DetectAndFilterEvents(self, grouping_pattern=None,  # pylint: disable=C0103
                              bool_indexes=None,
                              label_signal=None,
                              min_duration=None):
        """deprecated"""
        return self.detect_and_filter_events(grouping_pattern,
                                             bool_indexes,
                                             label_signal,
                                             min_duration)

    @deprecated('__detect_threshold_exceed')
    def __DetectThresholdExceed(self):  # pylint: disable=C0103
        """deprecated"""
        return self.__detect_threshold_exceed()

    def __ProcessSpecialIndexes(self, boolean_indexes):  # pylint: disable=C0103
        """seprecated"""
        return self.__process_special_indexes(boolean_indexes)

    @deprecated('__group_clothoid_events')
    def __GroupClothoidEvents(self, pattern):  # pylint: disable=C0103
        """deprecated"""
        return self.__group_clothoid_events(pattern)

    @deprecated('__filter_events_per_road_type')
    def __FilterEventsPerRoadType(self, label_signal):  # pylint: disable=C0103
        """deprecated"""
        return self.__filter_events_per_road_type(label_signal)

    @deprecated('__filter_events_by_duration')
    def __FilterEventsByDuration(self, nb_cycle_min=None):  # pylint: disable=C0103
        """deprecated"""
        return self.__filter_events_by_duration(nb_cycle_min)

    @deprecated('set_clothoid_parameters')
    def SetClothoidParameters(self, c0, c1, yaw, timing=False):  # pylint: disable=C0103
        """deprecated"""
        return self.set_clothoid_parameters(c0, c1, yaw, timing)

    @deprecated('set_ego_kinematics')
    def SetEgoKinematics(self, vdy_data, timing=False):  # pylint: disable=C0103
        """deprecated"""
        return self.set_ego_kinematics(vdy_data, timing)

    @deprecated('get_clothoid_event_list')
    def GetClothoidEventList(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_clothoid_event_list()

    @deprecated('generate_clothoid_plot')
    def GenerateClothoidPlot(self, c0, c1, yaw, speed, ego_motion, cog_arclength, output):  # pylint: disable=C0103
        """deprecated"""
        return self.generate_clothoid_plot(c0, c1, yaw, speed, ego_motion, cog_arclength, output)


class MultiThreading(Thread):
    """
    Used in order to process each file in multiple threads.
    """
    def __init__(self, id, thread_name, cog, c0, c1, yaw, ego, speed,
                 cycle_start, cycle_stop, Error, evaluation_samples, time_evaluation, indexes):
        """
        Sets all necessary attributes for processing.
        """
        self.id = id  # thread ID
        self.thread_name = thread_name  # thread Name
        self.cog = cog  # Ego path
        self.cyc_start = cycle_start  # Loop start
        self.cyc_stop = cycle_stop  # Loop end
        self.road_c0 = c0  # road's c0 curve
        self.road_c1 = c1  # road's c1 curve
        self.road_yaw = yaw  # road's yaw
        self.ego_motion = ego  # Ego motion
        self.speed = speed  # Ego vehicle's speed
        self.estimation_error = Error
        self.evaluation_samples = evaluation_samples
        self.time_evaluation = time_evaluation
        self.indexes = indexes
        Thread.__init__(self)  # Thread creation

    def run(self):
        """
        Each thread processes one section of the file.
        """
        for i in range(self.cyc_start, self.cyc_stop):
            if self.indexes is None or bool(self.indexes[i]) is True:
                clothoid = [self.road_c0[i], self.road_c1[i], self.road_yaw[i]]
                transformation_matrix = [self.ego_motion[6, i],
                                         self.ego_motion[5, i],
                                         self.ego_motion[0, i],
                                         self.ego_motion[1, i]]
                vehicle_speed = self.speed[i]
                if self.time_evaluation is True:
                    eval_samples = vehicle_speed * np.array(self.evaluation_samples)
                else:
                    eval_samples = self.evaluation_samples
                estimation_error = getroadtrajestimationerror(clothoid, transformation_matrix, self.cog, i,
                                                              eval_samples)

                if len(estimation_error) > 0:
                    for j in range(0, len(self.evaluation_samples)):
                        self.estimation_error[j, i] = estimation_error[j]


# --- Base clothoid event ---
class ValClothoidEvent(ValBaseEvent):
    # pylint: disable-msg = E1101
    """ Clothoid Event Class """
    # --- Attribute definitions ---
    BEGIN_ABSTS = "start ts"
    END_ABSTS = "end ts"
    EVENT_ATTR_C0 = "clothoidc0"
    EVENT_ATTR_C1 = "clothoidc1"
    EVENT_ATTR_YAW = "clothoidyaw"
    EVENT_ATTR_ERROR = "clothoidestimationerror"
    EVENT_ATTR_THRESHOLD = "clothoideventthreshold"
    EVENT_ATTR_TIME_SAMPLE = "clothoidtimesample"
    EVENT_ATTR_CONFIDENCE = "clothoidconfidence"
    EVENT_ATTR_TRACKSTAT = "clothoidtrackingstatus"

    def __init__(self, start_time, start_index, stop_time, stop_index,
                 eventtype=None, timestamps=None, seid=None, assessment_id=None):
        """
        Constructor for clothoid event.
        :param start_time: start timestamp of the event.
        :param start_index: start cycle index of the event.
        :param stop_time: stop timestamp for the event.
        :param stop_index: stop cycle index of the event.
        """
        self.__logger = util_log.Logger(self.__class__.__name__)

        ValBaseEvent.__init__(self, start_time=start_time,
                              start_index=start_index,
                              stop_time=stop_time,
                              stop_index=stop_index,
                              timestamps=timestamps,
                              seid=seid,
                              assessment_id=assessment_id)

        ValBaseEvent.SetType(self, eventtype)
#         if assessment_id is None:
#             # --- Sets a default assessment ---
#             ValBaseEvent.SetAssessment(self, 'Not assessed',
#                                        comment="Automatic assessment - Not assessed",
#                                        wfid=val_res.ValAssessmentWorkFlows.ASS_WF_MANUAL)

        self.AddAttribute('cycles', (stop_index - start_index), '', 'float')

        self.__start_idx = start_index
        self.__stop_idx = stop_index
        self.__vdy_data = None
        self.__road_type = None
        self.__estimationerror = None
        self.__time_sample = None
        self.__eventthreshold = None
        self.__roadc0 = None
        self.__roadc1 = None
        self.__roadyaw = None
        self.__roadconfidence = None
        self.__roadtrackstat = None

    def save_event_db(self, dbval, dbglbl, trid, collid, measid):
        """
        Save Event in Database, but before put all necessary data into
        event details container.

        :param dbval: VAL DB interface.
        :param dbglbl: GBL DB interface.
        :param trid: Testrun identifier.
        :param collid: CAT Collection ID.
        :param measid: Measurement Identifier.
        """
        ValBaseEvent.Save(self, dbval, dbglbl, trid, collid, meas_id=measid)

# --- Functions for setting the attributes of the event --------------------------------------------------------------

    def set_clothoid_params(self, curve0, curve1, yaw, timing=False):
        """
        Sets the road clothoid parameters y(x) = m * x + (c0 / 2) * x^2 + (c1 / 6) * x^3.

        :param curve0: c0.
        :param curve1: c1.
        :param yaw: m.
        :note input format: Either floats or list of floats.
        """
        self.__roadc0 = curve0
        self.__roadc1 = curve1
        self.__roadyaw = yaw
        start_idx = self.get_start_index()
        stop_idx = self.GetStopIndex()
        if timing is False:
            self.AddAttribute(self.EVENT_ATTR_C0, curve0[start_idx], '', 'float')
            self.AddAttribute(self.EVENT_ATTR_C1, curve1[start_idx], '', 'float')
            self.AddAttribute(self.EVENT_ATTR_YAW, yaw[start_idx], '', 'float')
        else:
            self.AddTimingAttribute(self.EVENT_ATTR_C0, curve0[start_idx:stop_idx], '', 'float')
            self.AddTimingAttribute(self.EVENT_ATTR_C1, curve1[start_idx:stop_idx], '', 'float')
            self.AddTimingAttribute(self.EVENT_ATTR_YAW, yaw[start_idx:stop_idx], '', 'float')

    def get_clothoid_params(self):
        """
        Returns c0,c1, yaw.
        """
        return self.__roadc0, self.__roadc1, self.__roadyaw

    def get_start_index(self):
        """ Returns the start index of the event.
        """
        return self.__start_idx

    def set_road_info(self, confidence, tracking_status, timing=False):
        """
        Sets road info parameters.

        :param confidence: confidence in the road estimation.
        :param tracking_status: tracking status.
        """
        self.__roadconfidence = confidence
        self.__roadtrackstat = tracking_status
        start_idx = self.get_start_index()
        stop_idx = self.GetStopIndex()
        if timing is False:
            self.AddAttribute(self.EVENT_ATTR_CONFIDENCE, confidence[start_idx], '', 'float')
            self.AddAttribute(self.EVENT_ATTR_TRACKSTAT, tracking_status[start_idx], '', 'float')
        else:
            self.AddTimingAttribute(self.EVENT_ATTR_CONFIDENCE, confidence[start_idx:stop_idx], '', 'float')
            self.AddTimingAttribute(self.EVENT_ATTR_TRACKSTAT, tracking_status[start_idx:stop_idx], '', 'float')

    def set_ego_kinematics(self, vdy_data, timing=False):
        """
        Sets the vehicle dynamics info.
        :param vdy_data: vdy_data dictionnary containing the necessary signals.
        """
        self.__vdy_data = vdy_data
        start_idx = self.get_start_index()
        stop_idx = self.GetStopIndex()
        try:
            if len(self.__vdy_data) > 0:
                if timing is True:
                    veh_speed = vdy_data["VehicleSpeed"][start_idx:stop_idx]
                    yawrate = vdy_data["VehicleYawRateObjSync"][start_idx:stop_idx]
                    acceleration = vdy_data["VehicleAccelXObjSync"][start_idx:stop_idx]
                    veh_curve = vdy_data["VehicleCurveObjSync"][start_idx:stop_idx]
                    self.AddTimingAttribute('acceleration', acceleration, '', 'float')
                    self.AddTimingAttribute('radius', veh_curve, '', 'float')
                    self.AddTimingAttribute('vehspeed', veh_speed, '', 'float')
                    self.AddTimingAttribute('yawrate', yawrate, '', 'float')
                else:
                    veh_speed = vdy_data["VehicleSpeed"][start_idx]
                    yawrate = vdy_data["VehicleYawRateObjSync"][start_idx]
                    acceleration = vdy_data["VehicleAccelXObjSync"][start_idx]
                    veh_curve = vdy_data["VehicleCurveObjSync"][start_idx]
                    self.AddAttribute('acceleration', acceleration, '', 'float')
                    self.AddAttribute('radius', veh_curve, '', 'float')
                    self.AddAttribute('vehspeed', veh_speed, '', 'float')
                    self.AddAttribute('yawrate', yawrate, '', 'float')
        except:
            raise ValEventError('Class Type of kinematic information is not correct')

    def get_vdy_data(self):
        """ Returns the vdy data at the time of the event.
        """
        return self.__vdy_data

    def set_estimation_error(self, error):
        """ Sets the estimation error attribute for the detected event.
        """
        self.__estimationerror = error
        if isinstance(error, float):
            self.AddAttribute(self.EVENT_ATTR_ERROR, error, 'meter', 'float')
        else:
            raise ValEventError('Time sample is a global attribute --> has to be a float')

    def get_estimation_error(self):
        """ Returns the estimation error for the current event.
        """
        return self.__estimationerror

    def set_time_sample(self, time_sample):
        """ Sets the time sample for which the event is detected.
        :param time_sample: time sample where the event is generated.
        """
        self.__time_sample = time_sample
        if isinstance(time_sample, float):
            self.AddAttribute(self.EVENT_ATTR_TIME_SAMPLE, time_sample, 'second', 'float')
        else:
            raise ValEventError('Time sample is a global attribute --> has to be a float')

    def set_road_type(self, road_type):
        """ Sets the road type.
        :param road_type: road type as a string.
        """
        self.__road_type = road_type
        if isinstance(road_type, float):
            self.AddAttribute(RDTYPE_DEFS.EVENT_ATTR_ROAD_TYPE, road_type, '', 'float')
        else:
            raise ValEventError('Road type is a global attribute --> has to be a float')

    def get_road_type(self):
        """
        Returns the road type for the event.
        :return: road type.
        """
        return self.__road_type

    def set_event_threshold(self, threshold):
        """ Sets the event triggering threshold used.
        :param threshold: event threshold in meters.
        """
        self.__eventthreshold = threshold
        if isinstance(threshold, float):
            self.AddAttribute(self.EVENT_ATTR_THRESHOLD, threshold, '', 'float')
        else:
            raise ValEventError('Threshold is a global attribute --> has to be a float')

    def set_event_image(self, buff):
        """
        Stores the event image in the database.

        :param buff: the image buffer.
        """
        self.AddAttribute(EVENT_ATTR_EVENT_IMAGE, image=buff)

    @deprecated('save_event_db')
    def SaveEventDB(self, dbval, dbglbl, trid, collid, measid):  # pylint: disable=C0103
        """
        :deprecated: use "save_event_db" instead
        """
        return self.save_event_db(dbval, dbglbl, trid, collid, measid)

    @deprecated('set_clothoid_params')
    def SetClothoidParams(self, curve0, curve1, yaw, timing=False):  # pylint: disable=C0103
        """
        :deprecated: use "set_clothoid_params" instead
        """
        return self.set_clothoid_params(curve0, curve1, yaw, timing)

    @deprecated('get_clothoid_params')
    def GetClothoidParams(self):  # pylint: disable=C0103
        """
        :deprecated: use "get_clothoid_params" instead
        """
        return self.get_clothoid_params()

    @deprecated('get_start_index')
    def GetStartIndex(self):  # pylint: disable=C0103
        """
        :deprecated: use "get_start_index" instead
        """
        return self.get_start_index()

    @deprecated('set_road_info')
    def SetRoadInfo(self, confidence, tracking_status, timing=False):  # pylint: disable=C0103
        """
        :deprecated: use "set_road_info" instead
        """
        return self.set_road_info(confidence, tracking_status, timing)

    @deprecated('set_ego_kinematics')
    def SetEgoKinematics(self, vdy_data, timing=False):  # pylint: disable=C0103
        """
        :deprecated: use "set_ego_kinematics" instead
        """
        return self.set_ego_kinematics(vdy_data, timing)

    @deprecated('get_vdy_data')
    def GetVDYData(self):  # pylint: disable=C0103
        """
        :deprecated: use "get_vdy_data" instead
        """
        return self.get_vdy_data()

    @deprecated('set_estimation_error')
    def SetEstimationError(self, error):  # pylint: disable=C0103
        """
        :deprecated: use "set_estimation_error" instead
        """
        return self.set_estimation_error(error)

    @deprecated('get_estimation_error')
    def GetEstimationError(self):  # pylint: disable=C0103
        """
        :deprecated: use "get_estimation_error" instead
        """
        return self.get_estimation_error()

    @deprecated('set_time_sample')
    def SetTimeSample(self, time_sample):  # pylint: disable=C0103
        """
        :deprecated: use "set_time_sample" instead
        """
        return self.set_time_sample(time_sample)

    @deprecated('set_road_type')
    def SetRoadType(self, road_type):  # pylint: disable=C0103
        """
        :deprecated: use "set_road_type" instead
        """
        return self.set_road_type(road_type)

    @deprecated('get_road_type')
    def GetRoadType(self):  # pylint: disable=C0103
        """
        :deprecated: use "get_road_type" instead
        """
        return self.get_road_type()

    @deprecated('set_event_threshold')
    def SetEventThreshold(self, threshold):  # pylint: disable=C0103
        """
        :deprecated: use "set_event_threshold" instead
        """
        return self.set_event_threshold(threshold)

    @deprecated('set_event_image')
    def SetEventImage(self, buff):  # pylint: disable=C0103
        """
        :deprecated: use "set_event_image" instead
        """
        return self.set_event_image(buff)


"""
CHANGE LOG:
-----------
$Log: clothoid.py  $
Revision 1.2 2015/10/08 17:21:28CEST Hospes, Gerd-Joachim (uidv8815) 
new param indexes for MultiThreading (by N.Ibrouchene), pep8 fixes
- Added comments -  uidv8815 [Oct 8, 2015 5:21:28 PM CEST]
Change Package : 380884:1 http://mks-psad:7002/im/viewissue?selection=380884
Revision 1.1 2015/04/23 19:04:51CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/obj/clothoid/project.pj
Revision 1.12 2015/02/06 16:46:27CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:46:28 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.11 2015/01/20 10:08:37CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 20, 2015 10:08:38 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.10 2014/09/25 13:29:13CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:14 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.9 2014/06/03 15:30:34CEST Hecker, Robert (heckerr)
updated with version from nassim + deprecation warnings.
--- Added comments ---  heckerr [Jun 3, 2014 3:30:34 PM CEST]
Change Package : 240753:1 http://mks-psad:7002/im/viewissue?selection=240753
Revision 1.8 2014/04/30 16:58:06CEST Hecker, Robert (heckerr)
reduced pep8.
--- Added comments ---  heckerr [Apr 30, 2014 4:58:07 PM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.7 2014/04/29 10:26:32CEST Hecker, Robert (heckerr)
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:33 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.6 2014/03/26 15:05:09CET Hecker, Robert (heckerr)
Updates for python 3 support.
--- Added comments ---  heckerr [Mar 26, 2014 3:05:09 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.5 2014/01/27 11:24:04CET Ibrouchene, Nassim (uidt5589)
Fixed a bug in the calculation of the number of threads. Changed eventtype
input parameter as optional for the clothoid event class.
--- Added comments ---  uidt5589 [Jan 27, 2014 11:24:05 AM CET]
Change Package : 213484:1 http://mks-psad:7002/im/viewissue?selection=213484
Revision 1.4 2013/12/03 17:33:07CET Sandor-EXT, Miklos (uidg3354)
pylint fix
--- Added comments ---  uidg3354 [Dec 3, 2013 5:33:07 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.3 2013/07/29 09:55:15CEST Ibrouchene, Nassim (uidt5589)
Uses Save instead of SaveEventDB for event save.
Clothoid error estimation can be chosen to be done with time based samples or
distance based samples.
--- Added comments ---  uidt5589 [Jul 29, 2013 9:55:15 AM CEST]
Change Package : 182606:2 http://mks-psad:7002/im/viewissue?selection=182606
Revision 1.2 2013/05/14 10:46:55CEST Ibrouchene-EXT, Nassim (uidt5589)
Moved some functions away from helper.py.
--- Added comments ---  uidt5589 [May 14, 2013 10:46:55 AM CEST]
Change Package : 182606:2 http://mks-psad:7002/im/viewissue?selection=182606
"""
