"""
sod_sacobserver.py
------------------

documentation of <sod_sacobserver>

:org:          Continental AG
:author:       Robert Maertin

:date:         2014/03/13


Every LoadData - ProcessData - PostProcessData cycle:

Reads eReturnState signal, finds onset, then stores on the bus:

- onset index (Portname: ONSET_INDEX_PORT_NAME) and
- time-stamp (Portname: ONSET_TIME_PORT_NAME) and a
- "skip_recording" (Portname: SKIP_RECORDING) flag

The onset time-stamp represents the point in time when the eReturnState signal
indicates sufficient calibration quality.
It should be used by other observers to determine whether KPI computation
should be started.

Special cases:

If the quality is never high enough, onset time will be the last timestamp in
the recording and the SKIP_RECORDING flag will be set to true.

If the eReturnState signal is not available, a warning will be given, the onset
time will be the first timestamp, so everything will be processed.


Prerequisites:

This observer is to be placed behind the SignalExtractor observer in the cfg.
The observer is to be passed the PortNames of the desired timestamp signal and
the eReturnState signal.

If these PortNames are not provided or if the signals behind these names are of
unequal length, the observer will throw an exception and output an error
message.



Here's an example snippet of the cfg setup::

    [Extractor]
    ClassName="SignalExtractor"
    PortOut=["RelevantObject"]
    InputData=[ ...
        ("ADDITIONAL_signals",
           [{'SignalName':'MTS.Package.TimeStamp',
               'PortName':'TimeStamp'},
                    ...
            {'SignalName':'MFC4xx Device.SAC.pSacOutput.eReturnState',
                'PortName':'eReturnState'},]),
            ("SignalExtractorConfig", {'EnableSODList'   :True,
                                    'DataSource'      :1 })]
    ConnectBus=["Bus#1"]
    Active=True
    Order=3

    [SODSACObserver]
    ClassName="SODSACObserver"
    InputData=[("TimestampName","Timestamp"), ("eReturnStateName","eReturnState"), ... ]
    ConnectBus=["Bus#1"]
    Active=True
    Order=4


Example usage::

    from sod_sacobserver import ONSET_TIME_PORT_NAME

    In an observer of your choice, during the cycle of
    LoadData->ProcessData->PostProcessData, read the valid onset time from the bus:

    on_ts = self._data_manager.GetDataPort(ONSET_TIME_PORT_NAME, "Bus#1")

    for ts in TS:
    if ts < on_ts
        continue

    # KPI Computation follows

"""


import sys

from stk.valf.base_component_ifc import BaseComponentInterface

ER_LOWER = 50
ER_UPPER = 59
ONSET_INDEX_PORT_NAME = "SAC_ER_WITHIN_RANGE_ONSET_INDEX"
ONSET_TIME_PORT_NAME = "SAC_ER_WITHIN_RANGE_ONSET_TIME"
SKIP_RECORDING = "SAC_ER_NEVER_WITHIN_RANGE"


class SODSACObserver(BaseComponentInterface):
    """
    find detailed description above on module `sac_observer`
    """
    # disable pylint check W0212: 'access to private member' used in 'LoadData() called' etc.
    # pylint: disable=W0212
    def __init__(self, data_manager, component_name, bus_name=None):
        version = "$Revision: 1.1 $"
        BaseComponentInterface.__init__(self, data_manager,
                                        component_name, bus_name, version)

        # Length of eReturnState signal. To be used for sanity check.
        self.__er_length = None

        msg = str(sys._getframe().f_code.co_name) + "()" + " called."
        self._logger.debug(msg)

    def __determine_onset(self):
        """
        Loads eReturnState signal and returns the index of the first occurrence
        of ER_LOWER <= signal[index] <= ER_UPPER.
        """
        sig_name = self._data_manager.GetDataPort("eReturnStateName",
                                                  self._bus_name)
        er_sig = self._data_manager.GetDataPort(sig_name, self._bus_name)
        self.__er_length = len(er_sig)
        onset = 0
        skip_recording = False
        if er_sig:
            try:
                onset = next(onset for onset, er in enumerate(er_sig)
                             if ER_LOWER <= er <= ER_UPPER)
            except StopIteration:
                msg = "Couldn't find acceptable eReturnstate value."
                self._logger.warning(msg)
                onset = self.__er_length - 1
                skip_recording = True
        else:
            msg = "eReturnState signal is None."
            self._logger.warning(msg)
        return onset, skip_recording

    def Initialize(self):
        msg = str(sys._getframe().f_code.co_name) + "()" + " called."
        self._logger.debug(msg)

        self._data_manager.SetDataPort(ONSET_INDEX_PORT_NAME, 0,
                                       self._bus_name)

        self._data_manager.SetDataPort(ONSET_TIME_PORT_NAME, None,
                                       self._bus_name)

        self._data_manager.SetDataPort(SKIP_RECORDING, False, self._bus_name)

        if self._data_manager.GetDataPort("eReturnStateName",
                                          self._bus_name) is None:
            msg = "eReturnStateName not available to observer."
            self._logger.error(msg)
            raise

        if self._data_manager.GetDataPort("TimestampName",
                                          self._bus_name) is None:
            msg = "TimestampName not available to observer."
            self._logger.error(msg)
            raise

        return 0

    # PostInitialize(self) not used

    def LoadData(self):
        msg = str(sys._getframe().f_code.co_name) + "()" + " called."
        self._logger.debug(msg)

        onset, skip_recording = self.__determine_onset()

        tstamp = self._data_manager.GetDataPort(self._data_manager.GetDataPort("TimestampName",
                                                                               self._bus_name),
                                                self._bus_name)

        if not self.__er_length == len(tstamp):
            msg = "Timestamp and eReturnState signal have different length."
            self._logger.error(msg)
            raise

        on_ts = tstamp[onset]
        self._data_manager.SetDataPort(ONSET_INDEX_PORT_NAME, onset,
                                       self._bus_name)
        self._data_manager.SetDataPort(ONSET_TIME_PORT_NAME, on_ts,
                                       self._bus_name)

        self._data_manager.SetDataPort(SKIP_RECORDING, skip_recording,
                                       self._bus_name)

        return 0

    # ProcessData(self): not used

    def PostProcessData(self):
        msg = str(sys._getframe().f_code.co_name) + "()" + " called."
        self._logger.debug(msg)
        self.__er_length = None
        self._data_manager.SetDataPort(ONSET_INDEX_PORT_NAME, 0,
                                       self._bus_name)
        self._data_manager.SetDataPort(ONSET_TIME_PORT_NAME, None,
                                       self._bus_name)
        self._data_manager.SetDataPort(SKIP_RECORDING, False, self._bus_name)

        return 0

    # PreTerminate(self): not used

    # Terminate(self): not used

"""
CHANGE LOG:
-----------
$Log: sac_observer.py  $
Revision 1.1 2015/04/23 19:05:52CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
Revision 1.3 2015/02/10 19:39:43CET Hospes, Gerd-Joachim (uidv8815) 
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:44 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.2 2014/08/20 17:20:12CEST Hospes, Gerd-Joachim (uidv8815) 
fix pep8  and pylint errors
--- Added comments ---  uidv8815 [Aug 20, 2014 5:20:13 PM CEST]
Change Package : 253121:1 http://mks-psad:7002/im/viewissue?selection=253121
Revision 1.1 2014/08/13 12:51:46CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/valf/obs/project.pj
"""
