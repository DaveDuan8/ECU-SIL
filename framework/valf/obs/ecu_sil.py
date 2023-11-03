"""
crt.ecu_sil.ecu_sil
-------------------
Module contains the ECU_SIL observer which is used to performs ECU SIL tests
"""

from datetime import datetime

from framework.io.signalreader import SignalReader
from framework.rep.pdf.algo_test.report import AlgoTestReport
from framework.rep.pdf.base.pdf import Story
from framework.rep.pdf.base.template import Style
from framework.util.defines import *
from framework.val.results import ValTestcase
from framework.valf import BaseComponentInterface
from math import floor

__author__ = "Leidenberger Ralf"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 21:39:25CET $"


DB_BUS = "DBBus#1"
DB_CON_DICT = "DatabaseObjectsConnectionsDict"
DB_OBJECTS = "DataBaseObjects"

ECU_SIL_CONFIG = "ECU_SIL_CONFIG"
SIL_BUS = "sil_bus"
ECU_BUS = "ecu_bus"
CFG_TC_LST = "Testcases"

TC_DESCRIPTION = "desc"
TC_EXPECTED_RESULT = "exp_res"
TC_DOORS_URL = "doors_url"
TC_SPEC_TAG = "specification_tag"
TC_NAME = "name"
TC_CLASS = "class"


class EcuSilObserver(BaseComponentInterface):
    """ Observer that executes the ECU SIL test to verify the correctness of
        the simulation.
        The test itself is structured into testcases which are executed
        separately.
    """

    def __init__(self, data_manager, component_name, bus_name):
        """ Prepare globally needed variables. """
        BaseComponentInterface.__init__(self, data_manager, component_name,
                                        bus_name)

        self._testrun = None
        self.config = None
        self.recordings = []
        self.testcase_clazz_map = []

        self.report = AlgoTestReport()
        # self.cat_db = None
        # self.obj_db = None
        # self.lbl_db = None
        # self.gbl_db = None
        # self.val_db = None

    def initialize(self):
        """
        Register the catalog db to the database
        """
        # data_base_objects = self._data_manager.get_data_port(DB_OBJECTS, DB_BUS)
        # data_base_objects.append(cat)

        return self.RET_VAL_OK

    def post_initialize(self):
        """ Establish connection to database and load all testcase
        from the configuration.
        """
        # self._connect_to_databases()

        self.config = self._data_manager.get_data_port(ECU_SIL_CONFIG)
        self._testrun = self._data_manager.get_data_port("trun")

        if self.config[CFG_TC_LST] is None or len(self.config[CFG_TC_LST]) == 0:
            msg = ("Configuration does not contain ANY testcases. " +
                   "Please check the configuration.")
            self._logger.warning(msg)
            return self.RET_VAL_ERROR

        coll_id = -1
        for testcase in self.config[CFG_TC_LST]:
            msg = "Executing testcase: '{0:}'".format(testcase[TC_NAME])
            self._logger.info(msg)

            val_testcase = ValTestcase(testcase[TC_NAME], coll_id,
                                       testcase[TC_SPEC_TAG],
                                       testcase[TC_DOORS_URL],
                                       testcase[TC_EXPECTED_RESULT],
                                       testcase[TC_DESCRIPTION])

            class_ = self._import_testcase_clazz(testcase[TC_CLASS])
            test_class = class_(self._data_manager, val_testcase, testcase)

            self.testcase_clazz_map.append((val_testcase, test_class, testcase,
                                            Story(Style())))
            self._testrun.add_test_case(val_testcase)

            # noinspection PyBroadException
            try:
                test_class.post_initialize()
            except:
                continue

        return self.RET_VAL_OK

    def _import_testcase_clazz(self, name):
        """ Method to load to classes by name.
            :param name:
        """
        try:
            cp = name.split(".")
            class_name = cp[-1]
            if len(cp[0:-1]) > 1:
                module_name = ".".join(cp[0:-1])
            else:
                module_name = cp[0]

            mod = __import__(module_name, fromlist=[class_name])
            class_ = getattr(mod, class_name)

            return class_
        except StandardError:
            self._logger.error("Failed to load testclass '{0:}'".format(name))
            raise

    def process_data(self):
        """ Performs all ECU SIL test cases. The testcases are
            compartmentalized in different %ses.
        """
        recording = self._data_manager.get_data_port("currentfile")
        self.recordings.append(recording)

        ecu60_reader = SignalReader(self._data_manager.get_data_port("CurrentSimFile", BUS_ECU_208), delim=",")
        sil60_reader = SignalReader(self._data_manager.get_data_port("CurrentSimFile", BUS_SIL_208), delim=",")
        ecu20_reader = SignalReader(self._data_manager.get_data_port("CurrentSimFile", BUS_ECU_207), delim=",")
        sil20_reader = SignalReader(self._data_manager.get_data_port("CurrentSimFile", BUS_SIL_207), delim=",")

        # Execute all coonfigured tests
        for tc_result, tc_class, tc_cfg, story in self.testcase_clazz_map:
            # Process distance and time
            # vdy = self._data_manager.get_data_port("VDY", BUS_ECU_207)
            # if vdy is not None:
            #     velocity = vdy["velocity"].values
            #     acceleration = vdy["acceleration"].values
            #     yaw_rate = vdy["yaw_rate"].values
            #     timestamps = vdy.index.values
            #     ego_motion_sil = EgoMotion(velocity, acceleration,
            #                                yaw_rate, timestamps)
            #
            #     meas = self._data_manager.get_data_port("currentfile")
            #     # meas_id = self.cat_db.GetMeasurementID(meas)
            #     meas_id = -1
            #
            #     tc_result.AddMeasDistTimeProcess(meas_id, ego_motion_sil)

            if ECU_BUS in tc_cfg.keys() and SIL_BUS in tc_cfg.keys():
                if tc_cfg[ECU_BUS].upper() == BUS_ECU_207.upper():
                    ecu_bsig_reader = ecu20_reader
                    ecu_bsig_reader2 = ecu60_reader
                else:
                    ecu_bsig_reader = ecu60_reader
                    ecu_bsig_reader2 = ecu20_reader
                if tc_cfg[SIL_BUS].upper() == BUS_SIL_207.upper():
                    sil_bsig_reader = sil20_reader
                    sil_bsig_reader2 = sil60_reader
                else:
                    sil_bsig_reader = sil60_reader
                    sil_bsig_reader2 = sil20_reader

                if not ecu_bsig_reader or not sil_bsig_reader:
                    self._logger.error("One of the configured busses is not available. Skipping current testcase.")
                    return

                tc_class.set_bsig_reader(ecu_bsig_reader, sil_bsig_reader, ecu_bsig_reader2, sil_bsig_reader2)

            tc_class.execute(story)

        ecu60_reader.close()
        sil60_reader.close()
        ecu20_reader.close()
        sil20_reader.close()

        # search and open bin files
        return self.RET_VAL_OK

    def _append_recordings_table(self, story):
        name = "Recordings"
        header = ["No.", "Filename", ]
        data = []
        for k in range(len(self.recordings)):
            meas_file = self.recordings[k]
            head, tail = os.path.split(meas_file)
            data.append([k+1, tail, ])

        column_widths = [25, 415, ]
        story.add_table(name, data, header=header, colWidths=column_widths)

    def pre_terminate(self, _processed_files="-", _processed_time=0):
        """ Build the final report, after all tests are performed and ready to
            be assessed.
        """
        for (_, test_class, _, _) in self.testcase_clazz_map:
            # noinspection PyBroadException
            try:
                test_class.pre_terminate()
            except:
                continue

        # Important, otherwise nothing gets writen into the database.
        # self.val_db.Commit()
        self._testrun._TestRun__processed_files = _processed_files

        self._testrun._TestRun__processed_time = floor(_processed_time / 1000000)
        print(self._testrun._TestRun__processed_files)
        self.report.set_test_run(self._testrun)

        # recordings overview
        self._append_recordings_table(self.report.developer)

        # Append all stories to chapter 3 (Development Details)
        for _, _, tc_cfg, story in self.testcase_clazz_map:
            heading = "Details for {0:}".format(tc_cfg[TC_NAME])
            self.report.developer.add_heading(heading, 1)

            # noinspection PyBroadException
            try:
                desc = tc_cfg["long_description"]
                self.report.developer.add_paragraph(desc)
            except:
                continue

            for s in story.story:
                self.report.developer.append(s)

        try:
            out_dir = self._data_manager.get_data_port("OutputDirPath")
            project = self._data_manager.get_data_port("ProjectName")
            base_name = "{0:}_ECU_SIL_TestReport_{1:}.pdf"
            build_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            file_name = base_name.format(project, build_date)
            self.report.build(os.path.join(out_dir, file_name))

            return self.RET_VAL_OK
        except Exception as ex:
            self._logger.error("Failed to build report. " + repr(ex))
            raise

"""
CHANGE LOG:
-----------
"""
