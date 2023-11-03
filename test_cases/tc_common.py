"""
ecu_sil_tool.test_cases.tc_common
---------------------

This module consist of the base class for all ECU SIL test cases and
some commonly needed methods for executing ECU SIL tests.
"""
from __future__ import print_function

import datetime
import logging
import os
import string

from framework.img.viz import PlotFactory
from framework.val.results import ValAssessment, ValAssessmentWorkFlows



__author__ = "Ralf Leidenberger"
__copyright__ = "Copyright 2014, Continental AG"
__version__ = "$Revision: 1.2 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/31 08:42:58CEST $"


def iso_datetime_str(date_time=datetime.datetime.now()):
    """ Returns the given datetime in iso format
    :param date_time:
    :return: iso date
    """
    return date_time.strftime("%Y-%m-%d %H:%M:%S")


class BaseTest(object):
    """ Base class for all ECU-SIL test cases. """
    def __init__(self, data_manager, testcase, config):
        """ Initializes the object.
            :param data_manager: ValF data manager facility
            :param testcase: The validation testcase
        """
        super(BaseTest, self).__init__()
        self._data_manager = data_manager
        self._logger = logging.getLogger(self.__class__.__name__)
        self.testcase = testcase
        self._config = config

        self.test_results = []

        self._ecu_bsig_reader = None
        self._sil_bsig_reader = None
        self._ecu_bsig_reader2 = None
        self._sil_bsig_reader2 = None

        # Make a separate dir for each test
        # valid_chars = "-_.() {}{}".format(string.ascii_letters, string.digits)
        valid_chars = "-_.(){}{}".format(string.ascii_letters, string.digits)
        plot_dir = "".join(c for c in config["name"] if c in valid_chars)
        base_output_path = self._data_manager.get_data_port("OutputDirPath")
        self.out_directory = os.path.join(base_output_path, plot_dir)

        if not os.path.exists(self.out_directory):
            os.mkdir(self.out_directory)

        self.plot_factory = PlotFactory(self.out_directory)

    def set_bsig_reader(self, ecu_bsig_reader, sil_bsig_reader, ecu_bsig_reader2, sil_bsig_reader2):
        """ Setter to add bsig readers to a testcase class.
        :param ecu_bsig_reader: A reader for ECU bsigs
        :param sil_bsig_reader: A reader for SIL bsigs
        :param ecu_bsig_reader2
        :param sil_bsig_reader2
        """
        self._ecu_bsig_reader = ecu_bsig_reader
        self._sil_bsig_reader = sil_bsig_reader

        self._ecu_bsig_reader2 = ecu_bsig_reader2
        self._sil_bsig_reader2 = sil_bsig_reader2

    def get_val_testcase(self):
        """ Returns the validation testcase for this test.
            :returns: The validation testcase
        """
        return self.testcase

    @staticmethod
    def _mk_assessment(result):
        """ Returns an automated validation assessment with the provided
            result.
            :param result: Result for the assessment
            :return: Assessment with the given result
        """
        uid = os.environ["USERNAME"]
        comment = "Automated assessment"
        issue = "N/A"

        assessment = ValAssessment(uid, ValAssessmentWorkFlows.ASS_WF_AUTO,
                                   result, comment, iso_datetime_str(),
                                   issue)
        return assessment

    def execute(self, story):
        """ Abstract method. Needs to be implemented by subclasses. """
        raise(NotImplementedError())

    def post_initialize(self):
        """ Add teststeps to testcase. """
        raise(NotImplementedError())

    def pre_terminate(self):
        """ Build the final report, after all tests are performed and ready to
            be assessed """
        raise(NotImplementedError())

"""
CHANGE LOG:
-----------
$Log: tc_common.py  $
Revision 1.2 2020/03/31 08:42:58CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 20:56:44CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/test_cases/project.pj

"""