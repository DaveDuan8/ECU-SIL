"""
time_checker.py
-------------------

Calculates the execution time based on the configured signal
and compares the values with stored values for the recording.

It can be configured to create a passed/failed result for the testrun
and writes a warning to the log in case of differences.

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `TimeChecker` (this module)

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/12 17:35:30CEST $
"""
# =====================================================================================================================
# Imports
# =====================================================================================================================
from os import path
from sys import path as sp
import inspect

PYLIB = path.abspath(path.join(path.dirname(inspect.currentframe().f_code.co_filename), "..", "..", ".."))
if PYLIB not in sp:
    sp.append(PYLIB)

from stk.valf.base_component_ifc import BaseComponentInterface as bci

import stk.valf.signal_defs as sig_gd
from stk.db.cat import cat
from stk.db.db_common import AdasDBError
from stk.valf.error import ValfError
from stk.valf.signal_defs import DBCONNECTION_PORT_NAME, DATABASE_OBJECTS_PORT_NAME

# =====================================================================================================================
# Global Definitions
# =====================================================================================================================
# allowed tolerance for time values to check: time +- deviation
# value depends on selected time signal, default value estimates microseconds
TIME_CHECK_DEVIATION = 5000


# =====================================================================================================================
# Classes
# =====================================================================================================================
class TimeChecker(bci):
    """
    observer class to compare the execution time (based on the configured time signal)
    with the value stored in CatDB for the recording. The result 'Passed'/'Failed' is pushed on the data bus.
    If no db connection is available the result will be 'NotAssessed'.

    The comparison is done during LoadData phase to stop the complete processing of the recording
    at early state in case of errors. Therefore this observer should be executed shortly after signal loading.

    To stop the processing of an incomplete simulated recording set data port TimeCheckAllowBreak;
    then LoadData will return with an error to end processing of the current recording and continue with the next.

    called by process manager in the states:

     - Initialize: get conf of time signal and additional configuration, request RecCatDb connection
     - PostInitialize: check CatDb connection
     - LoadData: calculate processed time and compare with stored value, set result if configured
     - PreTerminate: provide statistic on data bus

    Ports used on bus "global":

      - read  ``CurrentFile``: name of current rec file as listed in bpl file
      - read  ``CurrentSimFile``: name of current sim output file loaded by BplReader
      - read  ``TimeCheckSignalConf``: configured time signal and bus name:
                                        {'SignalName':<signal name>, 'BusName':<bus name>}
      - read  ``TimeCheckDeviation``: allowed tolerance of time values: time +- deviation
      - read  ``TimeCheckAllowBreak``: if True: break processing if time check fails
      - set   ``TimeCheckResult``: Passed/Failed/NotAssessed depending on comparison of start and stop time
      - set   ``TimeCheckStatistic``: dict with sumerized numbers: {'Passed': 0, 'Failed': 0, 'NotAssessed': 0}

    Ports used on bus of db_connector
      - read ``DataBaseObjects``: get db_obj['cat'] connection from ``DbLinker`` to read start/stop values
      - read ``DataBaseObjectsConnections``: get CatDb from old DBConnector to read start/stop values
        (don't use anymore, use DbLinker instead)

    """
    def __init__(self, data_manager, component_name, bus_name):
        """init the needed
        """
        bci.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.2 $")

        self._db_bus = None
        self.__cat_db = None
        self._allow_break = None
        self._deviation = 0
        self._statistic = {'Passed': 0, 'Failed': 0, 'NotAssessed': 0}

        self._signal_conf = {}

    # --- Framework functions. --------------------------------------------------
    def Initialize(self):
        """
        Reads configured settings like name of time signal and deviation

        default values:

          - data bus name: 'DBBus#1'
          - allowed deviation: TIME_CHECK_DEVIATION

        """
        self._logger.debug()
        self._db_bus = None

        self._set_data('TestCheckResult', None, self._bus_name)
        self._set_data('TestCheckStatistic', None, self._bus_name)

        # add CatDb to the database object list
        self._db_bus = self._get_data("DBBus", self._bus_name)
        if self._db_bus is None:
            self._db_bus = "DBBus#1"

        self._signal_conf = self._get_data("TimeCheckSignalConf", self._bus_name)
        if self._signal_conf is None:
            raise ValfError('TimeChecker config error - port TimeCheckSignalConf not set')
        self._allow_break = self._get_data("TimeCheckAllowBreak", self._bus_name)
        self._deviation = self._get_data("TimeCheckDeviation", self._bus_name)
        if self._deviation is None:
            self._deviation = TIME_CHECK_DEVIATION
        return sig_gd.RET_VAL_OK

    def PostInitialize(self):
        """
        Checks if connection to CatDb is available (set up during Initialize of `DBConnector`)
        If not all checks will result in 'NotAssessed'.
        """
        self._logger.debug()

        # Get the database connection
        databaseobjectsconnections = self._get_data("DataBaseObjectsConnections", self._db_bus)
        databaseobjects = self._get_data(DATABASE_OBJECTS_PORT_NAME, self._db_bus)
        if databaseobjectsconnections is not None:
            for connobject in databaseobjectsconnections:
                if connobject.ident_str == sig_gd.DBCAT:
                    self.__cat_db = connobject
                    break
        elif databaseobjects is not None and type(databaseobjects) is dict:
            self.__cat_db = self._get_data(DATABASE_OBJECTS_PORT_NAME, self._db_bus).get('cat')
        else:
            self._logger.error("No DataBase connection found! "
                               "Use DbLinker to set 'DataBaseObjects' "
                               "or old DBConnector setting 'DataBaseObjectsConnections'.")

        if self.__cat_db is None:
            self._logger.error("Database connection to recfile catalogue could not be established. "
                               "TimeCheck will always result in 'NotAssessed'.")

        return sig_gd.RET_VAL_OK

    def LoadData(self):
        """
        Get first and last time value and compare to start and stop values stored in CatDb for current recording
        """
        self._logger.debug()
        if self.__cat_db is None:
            self._set_data('TimeCheckResult', 'NotAssessed', self._bus_name)
            self._statistic['NotAssessed'] += 1
            return sig_gd.RET_VAL_OK

        # get current rec file name to retrieve start and stop from CatDb
        current_rec_file = self._get_data('CurrentFile', 'Global')
        if current_rec_file is None:
            self._logger.error("The port 'CurrentFile' is not available, no rec file name to check CatDb found.")
            return sig_gd.RET_VAL_ERROR
        # Get the current simulation file.
        current_sim_file = self._get_data("CurrentSimFile", 'global')
        if current_sim_file is None:
            self._logger.error("The port 'CurrentSimFile' is not available.")
            return sig_gd.RET_VAL_ERROR

        # finally get time signal from data port and call check
        time_signal = self._get_data(self._signal_conf['SignalName'], self._signal_conf['BusName'])
        result = self._time_check(current_rec_file, time_signal)
        self._set_data("TimeCheckResult", result, self._bus_name)
        self._statistic[result] += 1
        if result == 'Failed' and self._allow_break:
            return sig_gd.RET_VAL_ERROR

        return sig_gd.RET_VAL_OK

    def PreTerminate(self):
        """
        send statistic to data bus
        """
        self._logger.debug()
        self._set_data('TimeCheckStatistic', self._statistic, self._bus_name)

        return sig_gd.RET_VAL_OK

    def _time_check(self, rec_name, signal):
        """
        run the time check: get value from CatDb and compare start and stop using defined deviation.

        returns
         - 'Passed' if first and last time signal matches stored recording start and stop values with given tolerance
         - 'Failed' if signals are available but not inside tolerance
         - 'NotAssessed' if either CatDb entries are not available or time signal is empty

        :param rec_name: name of recording without extension as stored in CatDb and provided as CurrentFile
        :type rec_name:  string
        :param signal: signal array with time values, first and last are checked
        :type signal:  list of integers

        :return: result string
        :rtype:  'Passed'|'Failed'|'NotAssessed'
        """
        # get start and stop from CatDB
        try:
            measid = self.__cat_db.get_measurement_id(rec_name)
        except AdasDBError:
            self._logger.warning('no entry in CatDB for rec file %s, sim not assessed' % rec_name)
            return 'NotAssessed'
        else:
            meas_data, _ = self.__cat_db.get_measurement_with_sections(measid)
            rec_start = meas_data[cat.COL_NAME_FILES_BEGINTIMESTAMP]
            rec_stop = meas_data[cat.COL_NAME_FILES_ENDTIMESTAMP]

        if rec_start == 0 or rec_stop == 0:
            return 'NotAssessed'

        if abs(rec_start - signal[0]) > self._deviation or abs(rec_stop - signal[-1]) > self._deviation:
            self._logger.error('First and Last value of time signal does not match '
                               'Start and Stop time of recording %s with defined tolerance' % rec_name)
            return 'Failed'

        return 'Passed'


"""
CHANGE LOG:
-----------
 $Log: time_checker.py  $
 Revision 1.2 2016/08/12 17:35:30CEST Hospes, Gerd-Joachim (uidv8815) 
 use also DbLinker port for CatDb connection
 Revision 1.1 2015/04/23 19:05:53CEST Hospes, Gerd-Joachim (uidv8815)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
 Revision 1.5 2015/03/20 16:18:59CET Mertens, Sven (uidv7805)
 ident string defined in signal_defs
 --- Added comments ---  uidv7805 [Mar 20, 2015 4:18:59 PM CET]
 Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
 Revision 1.4 2015/02/06 08:17:26CET Mertens, Sven (uidv7805)
 removing deprecated calls
 --- Added comments ---  uidv7805 [Feb 6, 2015 8:17:27 AM CET]
 Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
 Revision 1.3 2015/01/20 10:34:56CET Mertens, Sven (uidv7805)
 pylint update
 Revision 1.2 2014/04/30 18:54:36CEST Hospes, Gerd-Joachim (uidv8815)
 add log entry in case of Failed check and TimeCheckAllowBreak handling with tests
 --- Added comments ---  uidv8815 [Apr 30, 2014 6:54:37 PM CEST]
 Change Package : 224325:1 http://mks-psad:7002/im/viewissue?selection=224325
 Revision 1.1 2014/04/30 18:02:28CEST Hospes, Gerd-Joachim (uidv8815)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/valf/obs/project.pj
"""
