"""
stk/util/classificator.py
--------

This file contains the classifier performance class.

:org:           Continental AG
:author:        Nassim Ibrouchene

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:29CEST $
"""
# pylint: disable=E1101
# Import Python Modules --------------------------------------------------------
import numpy as np
import operator

# Defines ----------------------------------------------------------------------
TRUE_POS = "True positive"
TRUE_NEG = "True negative"
FALSE_POS = "False positive"
FALSE_NEG = "False negative"


# Custom exceptions ------------------------------------------------------------
class ClassifierPerformanceError(Exception):
    """Base of all Event errors"""
    pass


class InputError(ClassifierPerformanceError):
    """ Input not properly selected """
    def __str__(self):
        return "Either the inputs don't have the same length or that length is equal to zero"


class ClassifierPerformance(object):
    """
    A class that is meant to provide means for assessing the performance of a
    multi-class classifier. From the two inputs signals values for
    true positives, true negatives, false positives and false
    negatives can be calculated, along with some other usefull data.

classifier output
     ^
     |
   C |                                       _________
     |                                      |         |
     |                                      |         |
   B |               _______________________|         |
     |              |                                 |
     |              |                                 |
   A |______________|                                 |______________________
      ----------------------------------------------------------------------->

labeled state
     ^
     |
   C |                                   ________________________
     |                                  |                       |
     |                                  |                       |
   B |                     _____________|                       |
     |                    |                                     |
     |                    |                                     |
   A |____________________|                                     |___________
      ---------------------------------------------------------------------->
    """

    def __init__(self, ego_mot=None):
        """
        Constructor method for the class.
        If EgoMotion class is given the class will compute the
        classifier performance based on time, otherwise based on cycles.

        :param ego_mot: EgoMotionClass used for time based calculation.
        :type ego_mot:  `EgoMotion`

        :note: The class handles either a cycle based computation or a
               time based computation, not both at the same time.
        """
        self.__ego_mot = ego_mot
        self.__classif_output = None
        self.__ground_truth = None
        self.__class_dict = None
        self.__index_pairs = dict()
        self.idxmap = dict()
        self.__confusion_matrix = None

    def compute(self, output, reference, categories):
        """
        This method compute the classifier performance based on a given
        classifier output and a given reference.

        :param output:       The output of the classification algo that is to be
                           compared to the ground thruth. This signal has to
                           contain only integer values for each cycle,
                           values that correspond to a class.
        :type output:        TBD
        :param reference:  The ground truth signal used to assess the
                           classification output signal. This signal has to
                           contain only integer values for each cycle,
                           values that correspond to a class.
        :type reference:   list[int] or list[float]
        :param categories: A category dictionary containing the classifier
                           categories names as keys, and the corresponding
                           signal values as dictionary values.
        :type categories:  dict{string: int}
        """
        # --- Check the validity of the input parameters ---

        if (len(output) != 0) and (len(output) == len(reference)):
            pass
        else:
            raise InputError

        # --- Class attributes ---
        self.__classif_output = output
        self.__ground_truth = reference
        self.__class_dict = categories
        self.__index_pairs = dict()
        self.idxmap = dict()
        # --- Indexes for confusion matrix, sorted by class signal value ---
        i = 0
        for _, cls in sorted(iter(self.__class_dict.items()), key=operator.itemgetter(1)):
            self.idxmap[cls] = i
            i += 1
        self.__confusion_matrix = np.zeros((len(self.__class_dict), len(self.__class_dict)))
        self.__get_contingency_table()

    def __get_contingency_table(self):
        """
        Computes the contingency table. If there are three classes A, B and C:
                      ----------------------
                     |                      |
                     |        Predicted     |
                      ----------------------
                     |   A  |   B   |   C   |
         -----------------------------------
        |       | A  |      |       |       |
        |       |---------------------------
        |Actual | B  |      |       |       |
        |       |---------------------------
        |       | C  |      |       |       |
         -----------------------------------
        """

        for name, cls in self.__class_dict.items():
            self.__index_pairs[name] = dict()
            clasif = (np.array(self.__classif_output) == cls)
            grdtrh = (np.array(self.__ground_truth) == cls)
            ret = self.__get_contigency_values(clasif, grdtrh)
            self.__index_pairs[name][TRUE_POS] = ret[0]
            self.__index_pairs[name][TRUE_NEG] = ret[1]
            self.__index_pairs[name][FALSE_POS] = ret[2]
            self.__index_pairs[name][FALSE_NEG] = ret[3]
            # Fill confusion matrix
            if self.__ego_mot is None:
                self.__set_confusion_matrix_cb(cls,
                                               self.__index_pairs[name][TRUE_POS],
                                               self.__index_pairs[name][FALSE_NEG])
            else:
                self.__set_confusion_matrix_tb(cls,
                                               self.__index_pairs[name][TRUE_POS],
                                               self.__index_pairs[name][FALSE_NEG])

    @staticmethod
    def __get_contigency_values(classificator, ground_truth):
        """
        Computes the true positive, true negative, false positive and
        false negatives for a single class.

        :param classificator: A binary signal, derived from self.__classif_output,
                              where the non zero cycles are the ones matching
                              a single class.
        :type classificator:  TBD
        :param ground_truth:  A binary signal, derived from self.__ground_truth,
                              where the non zero cycles are the ones matching
                              a single class.
        :return: A list: [true positive, true negative, false positive, false negatives]
        :rtype: list[????]
        """
        # Perform logical operations in order to get the contingency values
        false = np.logical_xor(classificator, ground_truth)
        true = np.logical_not(false)
        false_neg = np.logical_and(false, ground_truth)
        false_pos = np.logical_xor(false_neg, false)
        true_pos = np.logical_and(true, ground_truth)
        true_neg = np.logical_xor(true_pos, true)
        # --- Get the data ---
        edges = np.convolve(false_neg, [1, -1])
        fn_indexes = list(np.nonzero(edges)[0])
        edges = np.convolve(false_pos, [1, -1])
        fp_indexes = list(np.nonzero(edges)[0])
        edges = np.convolve(true_neg, [1, -1])
        tn_indexes = list(np.nonzero(edges)[0])
        edges = np.convolve(true_pos, [1, -1])
        tp_indexes = list(np.nonzero(edges)[0])

        return [tp_indexes, tn_indexes, fp_indexes, fn_indexes]

# --- Cycle based processing methods -------------------------------------------
    #===========================================================================
    # Index pair list: [0 10 10 15]. This represents two sections,
    # one from cycles 0 to 10 (10 excluded), and another
    # one from 10 to 15 (15 excluded).
    #===========================================================================
    @staticmethod
    def __get_cycle_count(idx_list):
        """
        Counts the number of cycles in an index pair list.

        :param idx_list: The index pair list.
        :type idx_list:  TBD
        :return:         count, the number of cycles inside that list.
        :rtype:          TBD
        """
        count = 0
        i = 0
        while i < len(idx_list) - 1:
            count += idx_list[i + 1] - idx_list[i]
            i += 2
        return count

    def __set_confusion_matrix_cb(self, cls, idx_list_true_pos, idx_list_false_neg):
        """
        Fills the confusion matrix using cycle based values from a single class
        (Fills a line in the matrix).

        :param cls:                The class index.
        :type cls:                 TBD
        :param idx_list_true_pos:  Index pair list for the true positives.
        :type idx_list_true_pos:   TBD
        :param idx_list_false_neg: Index pair list for the false negatives.
        :type idx_list_false_neg:  TBD
        """
        # --- Use True positives to fill the diagonal elements ---
        i = 0
        while i < len(idx_list_true_pos) - 1:
            for idx in range(idx_list_true_pos[i], idx_list_true_pos[i + 1]):
                self.__confusion_matrix[self.idxmap[cls], self.idxmap[cls]] += 1.0
            i += 2
        # --- Use False negatives to fill the lines ---
        i = 0
        while i < len(idx_list_false_neg) - 1:
            for idx in range(idx_list_false_neg[i], idx_list_false_neg[i + 1]):
                self.__confusion_matrix[self.idxmap[cls], self.idxmap[self.__classif_output[idx]]] += 1.0
            i += 2

# --- Time Based processing methods --------------------------------------------
    def __get_time_count(self, idx_list):
        """
        Counts the time in an index pair list.

        :param idx_list: The index pair list.
        :type idx_list:  TBD
        :return:         count, total time in seconds of the sections
                         inside the index pair list.
        :rtype:          TBD
        """
        count = 0.0
        i = 0
        while i < len(idx_list) - 1:
            start = idx_list[i]
            stop = idx_list[i + 1]
            count += np.sum(self.__ego_mot.get_cycle_time()[start:stop])
            i += 2
        return count

    def __set_confusion_matrix_tb(self, cls, idx_list_true_pos, idx_list_false_neg):
        """
        Fills the confusion matrix using time based values from a single class
        (Fills a line in the matrix).

        :param cls:                The class index.
        :type cls:                 TBD
        :param idx_list_true_pos:  Index pair list for the true positives.
        :type idx_list_true_pos:   TBD
        :param idx_list_false_neg: Index pair list for the false negatives.
        :type idx_list_false_neg:  TBD
        """
        # --- Use True positives to fill the diagonal elements ---
        i = 0
        while i < len(idx_list_true_pos) - 1:
            start = idx_list_true_pos[i]
            stop = idx_list_true_pos[i + 1]
            tmp = np.sum(self.__ego_mot.get_cycle_time()[start:stop])
            self.__confusion_matrix[self.idxmap[cls], self.idxmap[cls]] += tmp
            i += 2
        # --- Use False negatives to fill the lines ---
        i = 0
        while i < len(idx_list_false_neg) - 1:
            self.__set_timings(cls, [idx_list_false_neg[i], idx_list_false_neg[i + 1]])
            i += 2

    def __set_timings(self, clas, portion):
        """
        For a false negative portion, get the duration for each wrong class
        and set the values in the confusion matrix.

        :param clas:    The class.
        :type clas:     TBD
        :param portion: The portion, taken from an index pair list.
        :type portion:  TBD
        """
        for _, cls in self.__class_dict.items():
            if cls != clas:
                # --- Get the cycles where there is a match ---
                match = np.array(self.__classif_output[portion[0]:portion[1]]) == cls
                matching_idx = np.nonzero(match == 1)
                time_vec = np.zeros((portion[1] - portion[0]))
                time_slice = self.__ego_mot.get_cycle_time()[portion[0]:portion[1]]
                time_vec[matching_idx] = time_slice
                self.__confusion_matrix[self.idxmap[clas], self.idxmap[cls]] += np.sum(time_vec)

# --- Public methods -----------------------------------------------------------
    def get_confusion_matrix(self):
        """
        :return: the confusion matrix, as an numpy squared array of size number_of_classes.
        :rtype: TBD
        """
        return self.__confusion_matrix

    def get_result_for_class(self, name):
        """
        Returns the classification results for a single class.

        :param name: The class name.
        :type name:  string
        :return:     class_result, the result dictionary for the single class.
        :rtype:      TBD
        """
        class_result = dict()
        for metric, idx_list in self.__index_pairs[name].items():
            if self.__ego_mot is not None:
                class_result[metric] = self.__get_time_count(idx_list)
            else:
                class_result[metric] = self.__get_cycle_count(idx_list)
        return class_result

# --- Performance measures -----------------------------------------------------
    def get_sensitivity(self, class_name):
        """
        Returns the true positive rate (sensitivity) for a given class.

        :param class_name: The class name.
        :type class_name:  string
        :return:           The sensitivity
        :rtype:            float
        """
        class_raw = self.get_result_for_class(class_name)
        nom = float(class_raw[TRUE_POS])
        denom = nom + float(class_raw[FALSE_NEG])
        if denom: 
            onomnom = nom / denom
        else: 
            onomnom = 0.0

        return onomnom

    def get_specificity(self, class_name):
        """
        Returns the true negative rate (specificity) for a given class.

        :param class_name: The class name.
        :type class_name:  string
        :return:           The specificity
        :rtype:            float
        """
        class_raw = self.get_result_for_class(class_name)
        nom = float(class_raw[TRUE_NEG])
        denom = nom + float(class_raw[FALSE_POS])
        if denom:
            onomnom = nom / denom
        else:
            onomnom = 0.0

        return onomnom

    def get_correlation_coefficient(self, class_name):
        """
        Returns the correlation coefficient for the given class.

        :param class_name: The class name.
        :type class_name:  string
        :return:           The correlation coefficient
        :rtype:            float
        """
        class_raw = self.get_result_for_class(class_name)
        true_pos = float(class_raw[TRUE_POS])
        true_neg = float(class_raw[TRUE_NEG])
        false_pos = float(class_raw[FALSE_POS])
        false_neg = float(class_raw[FALSE_NEG])

        tmp1 = true_pos + false_neg
        tmp2 = true_pos + false_pos
        tmp3 = true_neg + false_pos
        tmp4 = true_neg + false_neg

        nom = true_pos * true_neg - false_pos * false_neg
        denom = np.sqrt(tmp1 * tmp2 * tmp3 * tmp4)

        onomnom = nom / denom
        
        if np.isnan(onomnom):
            onomnom = 0.0

        return onomnom

    def get_section_details(self, class_name, key):
        """
        Returns the section details for the desired class and key.

        :param class_name: The class name.
        :type class_name:  string
        :param key:        One of: TRUE_POS, TRUE_NEG, FALSE_POS, FALSE_NEG.
        :rtype:            TBD
        """
        if key in self.__index_pairs[class_name]:
            return self.__index_pairs[class_name][key]
        else:
            raise ClassifierPerformanceError("Invalid key")

"""
CHANGE LOG:
-----------
$Log: class_perf.py  $
Revision 1.1 2015/04/23 19:05:29CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.3 2015/02/13 13:25:33CET Hospes, Gerd-Joachim (uidv8815) 
fix div by zero error
--- Added comments ---  uidv8815 [Feb 13, 2015 1:25:33 PM CET]
Change Package : 306414:1 http://mks-psad:7002/im/viewissue?selection=306414
Revision 1.2 2015/01/22 14:29:21CET Ellero, Stefano (uidw8660) 
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 22, 2015 2:29:22 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.1 2014/03/26 17:44:57CET Hecker, Robert (heckerr) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
