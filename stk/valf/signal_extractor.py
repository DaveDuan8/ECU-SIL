"""
signal_extractor.py
-------------------

Extracts signal data from binary file format.

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `SignalExtractor` (this module)

:org:           Continental AG
:author:        Ovidiu Raicu

:version:       $Revision: 1.7 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/10/05 10:35:31CEST $
"""
# =====================================================================================================================
# Imports
# =====================================================================================================================
from os import path
from sys import path as sp, exit as sexit, _getframe
import time
from inspect import currentframe
from gc import collect
from numpy import array as narray, delete

PYLIB = path.abspath(path.join(path.dirname(currentframe().f_code.co_filename), "..", ".."))
if PYLIB not in sp:
    sp.append(PYLIB)

from stk.valf.base_component_ifc import BaseComponentInterface as bci

import stk.valf.signal_defs as sig_gd
from stk.io.signalreader import SignalReader, SignalReaderException
from stk.obj.generic_objects import GenericObjectList, GenericRectObject
from stk.valf.additional_object_list import AdditionalObjectList


# =====================================================================================================================
# Global Deffinitions
# =====================================================================================================================
# Speed test
SPEED_TEST = False

# Component names
GLOBAL_NAME = "Global"

# Other defines
OBJ_MIN_LIFETIME_DEFAULT = 10
INVALID_OBJECT = [255, -1]
IGNORE_OOI_FIRST_CYCLES = 10
DATA_SOURCE_SIM = 1
DATA_SOURCE_DEVICE = 2
SOD_OBJ_TRUE = [1, 2, 3]

# Ports for object list
PORT_NAME_OBJ_PREFIX = "OBJ_prefix"
PORT_NAME_OBJ_SIGNALS = "OBJ_signals"
PORT_NAME_OBJ_GENERIC_LIST = "OBJ_generic_object_list"
PORT_NAME_OBJ_COUNT = "OBJ_number_of_objects"
PORT_NAME_OBJ_MIN_LIFETIME = "OBJ_min_lifetime"

PORT_NAME_ADD_OBJ_SIGNALS = "AOJ_signals"
PORT_NAME_ADD_OBJ_MAP = "AOJ_mapping"
PORT_NAME_ADD_OBJ_LIST_SIZE = "AOJ_list_size"
PORT_NAME_ADD_OBJ_PREFIX = "AOJ_prefix"

# Ports for OOI
PORT_NAME_OOI_PREFIX = "OOI_prefix"
PORT_NAME_OOI_SIGNALS = "OOI_signals"
PORT_NAME_OOI_COUNT = "OOI_number_of_objects"

# Ports for FCT
PORT_NAME_FCT_PREFIX = "FCT_prefix"
PORT_NAME_FCT_SIGNALS = "FCT_signals"

# Ports for VDYD
PORT_NAME_VDY_PREFIX = "VDY_prefix"
PORT_NAME_VDY_SIGNALS = "VDY_signals"

# Ports for Ibeo data
PORT_NAME_IBEO_OBJ_PREFIX = "IbeoOut_Prefix"
PORT_NAME_IBEO_OBJ_SIGNALS = "IbeoOut_ObjSignals"
PORT_NAME_IBEO_OBJ_LENGTH = "IbeoOut_Length"
PORT_NAME_IBEO_OBJ_COUNT = "IbeoOut_Count"

# Ports for SOD data
PORT_NAME_SOD_OBJ_PREFIX = "SODOut_Prefix"
PORT_NAME_SOD_OBJ_SIGNALS = "SODOut_ObjSignals"
PORT_NAME_SOD_OBJ_LENGTH = "SODOut_Length"
PORT_NAME_SOD_OBJ_COUNT = "SODOut_Count"

# Extra ports
PORT_NAME_ADDIT_SIGNALS = "ADDITIONAL_signals"
PORT_NAME_CONST_SIGNALS = "Constant_signals"
PORT_NAME_PERMITTED_EMPTY_SIGNALS = "PermittedEmptySignals"

# HIL & SIL port with dict names
PORT_NAME_HIL_CONFIG = 'HilValidationConfig'
PORT_NAME_SIL_SYNC_CONFIG = 'SilSilSyncConfig'
ENABLE_TIME_CONVERSION = 'EnableTimeConversion'
ENABLE_FRAME_CONVERSION = 'EnableFrameConversion'
ORI_TIME_FILE_EXT = 'OriTimeFileExtension'
SYNC_SIGNAL = 'SyncSignalName'
SIL_SYNC_VIA_TS = 'ImageTS'
SIL_SYNC_VIA_FI = 'FrameID'
SIL_SYNC_SIGNAL = 'SilSyncSignalName'
SIL_TS_ABSOLUTE_TS = 'SIM Image Right.AbsoluteTimestamp'  # hard coded
SIL_IMAGE_TS = 'SIM Image Right.ImageTimestamp'
SIL_FC_ABSOLUTE_TS = 'AbsoluteTimestamp'  # hard coded
SIL_FRAME_CNR = 'FrameCounter'
SIL_SYNC_TS = 'AbsoluteTimestamp'
HIL_TIME_SIGNAL = 'HilTimeSignalName'
ORI_TIME_SIGNAL = 'OriTimeSignalName'
HIL_TMSTAMP_FILE_EXT = 'tstp'

# Output ports
PORT_NAME_EXTRACTOR_CONFIG = "SignalExtractorConfig"

# Other
PORT_NAME_REL_OBJ_ID = "rel_obj_id"
PORT_NAME_UILIFETIME = "uiLifeTime"
PORT_NAME_EOBJMAINTENANCESTATE = "eObjMaintenanceState"
PORT_NAME = "PortName"
SIGNAL_NAME = "SignalName"
COUNT = "Count"

# Ibeo Port Names
PORT_NAME_IBEO_OBJ_ID = "ObjID"

# Modules
MOD_OBJ = "OBJ"
MOD_OOI = "OOI"
MOD_FCT = "FCT"
MOD_VDY = "VDY"

# Default configuration for data extractor
DEFAULT_SIGNAL_EXTRACTOR_CONFIGURATION = {'EnableOBJList': False,
                                          'EnableOOIList': False,
                                          'EnableFCTData': False,
                                          'EnableVDYData': False,
                                          'DataSource': DATA_SOURCE_SIM}


# =====================================================================================================================
# Classes
# =====================================================================================================================
class SafeGuard(object):
    """Simple safeguard class"""
    def __init__(self, func_pointer):
        """
        Constructor for SafeGuard class

        :param func_pointer: function name to be called when the instance of the SafeGuard instance is destroyed
        """
        self.func_pointer = func_pointer

    def __del__(self):
        """
        for SafeGuard class: calls the function, which was given in the constructor
        """
        self.func_pointer()


class SigExtrReader(SignalReader):
    """internal class extending SignalReader

    allows to check the getitem output and supress the exception if a signal is permitted to be empty
    """
    def __init__(self, filename, permitted_empties, **kwargs):
        """initialize a reader

        :param filename: signal file path and name, passed to ``SignalReader``
        :type  filename: str
        :param permitted_entries: strings to search for in signal names not found by ``SignalReader``
        :type  permitted_entries: list
        """
        self._reader = SignalReader(filename, **kwargs)
        self.__permitted_empties = permitted_empties

    def __getitem__(self, signal):
        """check in case of exception if signal is in permitted list

        :param signal: signal name to get values for
        :type  signal: str
        :returns: signal content or None
        """
        try:
            return self._reader[signal]
        except SignalReaderException as ex:
            if any(s in signal for s in self.__permitted_empties):
                return None
            else:
                raise ex


class SignalExtractor(bci):  # pylint: disable=R0902,R0923
    r"""
    SignalExtractor is an observer class to extract single signals or signal objects from simulation result file

    called by process manager in the states:

     - `Initialize`: get lists of signals and signal objects to register ports and prepare extraction
     - `LoadData`: extract configured signals and objects to given ports
     - `PostProcessData`: clear ports and internal lists to prepare next extraction

    For configuring the signal extractor to be used by a validation observer please check the following examples

    **Validation Configuration(.cfg) file:**

    *1) Get the list of recordings*

        Before using the Signal Extractor, get the list of recordings, in order to iterate through bsig file per
        recording.

        There are two ways to get the list of recordings using the Validation Configuration(.cfg) file.

    i) Either from a Batch Play List (bpl), using `BPLReader` Class in VALF Configuration(.cfg) File:

    .. python::
        [BPLReader]
        ClassName="BPLReader"
        PortOut=[ "CurrentMeasFile", "CurrentSimFile"]
        InputData=[("SimFileExt", "bsig"), ("ExactMatch", True)]
        ConnectBus=["Bus#1"]
        Active=True
        Order=1

    i) Or, from a Collection in Database, using `CATReader` Class in VALF Configuration(.cfg) File:

    .. python::
        [CATReader]
        ClassName="CATReader"
        PortOut=[ "CurrentMeasFile", "CurrentSimFile"]
        InputData=[("SimFileExt", "bsig")]
        ConnectBus=["Bus#1"]
        Active=True
        Order=1
    ..

    *2) SignalExtractor Section in the VALF Configuration(.cfg) File:*

    .. python::
        [SignalExtractor]
        ClassName    = "SignalExtractor"
        InputData    = [("SignalExtractorConfig", {'EnableOBJList'   :True,
                                                   'EnableOOIList'   :True,
                                                   'EnableFCTData'   :True,
                                                   'EnableVDYData'   :True,
                                                   'DataSource'      :1 }),

            ("OBJ_min_lifetime",        20),
            ("OBJ_number_of_objects",   62),
            ("OOI_number_of_objects",   6),

            ("OBJ_prefix",             "SIM VFB ALL."),
            ("OOI_prefix",             "SIM VFB ALL.AlgoSenCycle."),
            ("FCT_prefix",             "SIM VFB ALL.AlgoVehCycle."),
            ("VDY_prefix",             "SIM VFB ALL.DataProcCycle"),

            ("OBJ_signals", [
                {'SignalName':"DataProcCycle.EmGenObjectList.aObject[%].Kinematic.fDistX",       'PortName':'DistX'},
                {'SignalName':"DataProcCycle.EmGenObjectList.aObject[%].Kinematic.fDistY",       'PortName':'DistY'},
                {'SignalName':"DataProcCycle.EmGenObjectList.aObject[%].Kinematic.fVrelX",       'PortName':'VrelX'}]),

            ("OOI_signals", [
                {'SignalName':"gSI_OOI_LIST.SI_OOI_LIST[%].object_id",             'PortName':'object_id'},
                {'SignalName':"gSI_OOI_LIST.SI_OOI_LIST[%].object_class",          'PortName':'object_class'}]),

            ("VDY_signals", [
                {'SignalName':'ObjSyncEgoDynamic.Longitudinal.MotVar.Velocity',     'PortName':'VehicleSpeed'},
                {'SignalName':'ObjSyncEgoDynamic.Longitudinal.MotVar.Accel',        'PortName':'VehicleAccelX'}]),

            ("FCT_signals", [
                {'SignalName': "pHEADOutputCustom.sWarnings.eAcuteDynamicWarning",         'PortName':"DynAcuteWarn"},
                {'SignalName': "pHEADOutputCustom.sPreBrake.bPreBrakeDecelEnabled",        'PortName':"PreBrake"}]),

            ("ADDITIONAL_signals", [
                {'SignalName':"MTS.Package.TimeStamp",                                     'PortName':'Timestamp'},
                {'SignalName':"SIM VFB ALL.DataProcCycle.Road.LaneWidth.eLaneWidthClass",  'PortName':'LaneWidth'}])]

        PortOut        = []
        ConnectBus    = ["Bus#1"]
        Order        = 2
    ..

        *NOTE:*

        The SignalExtractor .cfg file contains some Keywords in InputData which have special meaning.

        Below you can find short description about those keywords:

        *EnableOBJList*, *EnableOOIList*, *EnableFCTData* and *EnableVDYData* = boolean switches "True" or "False"
        for OBJ (Object Signals), OOI (Object of Interest Signals), FCT, VDY data signals

        *DataSource* = the number of DataSources available

        *OBJ_min_lifetime* = the filter to used for OBJ_signals, where a condition could be set of the lifetime
        of object

        *OBJ_number_of_objects* = the total number of Objects in the Object List

        *OOI_number_of_objects* = the total number of Objects in the OOI Object List

        *OBJ_prefix*, *OOI_prefix*, *FCT_prefix*, *VDY_prefix* = Prefixes for corresponding data signals

        *OBJ_signals*, *OOI_signals*, *VDY_signals*, *FCT_signals* = data signals with their own prefixes,
        with different port names

        *[%]* = a feature used by *OBJ_signals* and *OOI_signals*, where index value is from *0* to
        *OBJ_number_of_objects* or *OOI_number_of_objects*

        *ADDITIONAL_signals* = additional signals that are not included in *OBJ*, *OOI*, *FCT* or *VDY* signals.
        The rule is actually flexibile if a singal should be added to data signals (OBJ, OOI, FCT, VDY) or
        additional signals.

        *PermittedEmptySignals* = list of signals that are permitted to be empty, on default SignalExtractor claims
        an error for empty signals and stops executing the rec file, for listed signals only a warning is logged
        and None is returned as signal value. Any string in this list marks signal names containing it as permitted
        to be empty: ['Object'] matches 'Objects[%].General.eObjMaintenanceState' and 'MTS.Package.ObjectList'.

    *3) Configure example VALF Observer in the Configuration(.cfg) file*

    .. python::
        [My_Example_VALF_Observer]
        ClassName="ExampleObserver"
        PortOut=[]
        InputData=[]
        ConnectBus=["Bus#1"]
        Order=3

    **Python Script with Example VALF Observer Class:**

    .. python::
        import stk.valf.signal_defs as sigdef
        from stk.valf import BaseComponentInterface as bci
        from stk.obj.generic_objects import GenObjList

        class ExampleObserver(bci):
            def Initialize(self):
                # First function called after __init__. Followed by a call to PostInitialize.
                ...
            def PostInitialize(self):
                # Is called after all the component have been initialized.
                ...
            def LoadData(self):
                # LoadData. Called for each file.

                # To get all registered port names defined in the SignalExtractor section of .cfg file
                key_names = self._data_manager.get_registered_ports('Bus#1')

                # To get a single port name data for e.g. 'Timestamp'
                self._timestamp = self._data_manager.GetDataPort('Timestamp', 'Bus#1')

                # To get the instance of Generic Object List
                signal_names = ['DistX', 'DistY', 'VrelX']
                self.__generic_object_list = GenObjList(data_manager=self._data_manager,
                                                        bus_name='Bus#1',
                                                        sig_names=signal_names,
                                                        distx_sig_name=None,
                                                        disty_sig_name=None,
                                                        velx_sig_name=None)
                ...
            def ProcessData(self):
                # ProcessData. Called for each file.
                ...
            def PostProcessData(self):
                # PostProcessData. Called for each file.
                ...
            def PreTerminate(self):
                # Perform all actions required after the file processing loop is complete.
                ...
            def Terminate(self):
                # Perform all actions required after the file processing loop is complete.
    ..

        *NOTE:*

        - `DataManager`: handling ports to exchange data between components.
        - `stk.obj.GenObjList`: is used to get generic object list for object matching.

    **Main Python Script using the Validation Framework:**

    .. python::

        # Import valf module
        from stk.valf import valf

        # the VALF Observer plugin directory
        PLUGIN_FOLDER = r"D:\sandbox\Testing\Test_Environment\example_observer\"

        # the Output Folder for logging
        OUTPUT_FOLDER = r"D:\sandbox\Testing\Test_Data\Output\"

        # set output path for logging ect., logging level and directory of plugins (if not subdir of current HEADDIR):
        vsuite = valf.Valf(OUTPUT_FOLDER, INFO, PLUGIN_FOLDER, clean_folder=False)
        # from logging import INFO

        # mandatory: set config file and version of sw under test
        vsuite.LoadConfig(r'demo\\cfg\\demo.cfg')
        vsuite.SetSwVersion('AL_STK_V02.00.06')

        # additional defines not already set in config files or to be overwritten:
        vsuite.SetBplFile(r'cfg\\recordings.bpl')
        vsuite.SetSimPath(r'\\Lifs010.cw01.contiwan.com\data\SMFC4B0\_Validation\EBA')

        # start validation:
        vsuite.Run()

    **Time Synchronization**

        During LoadData the TimeStamps can be synchronised to values used for labeling,
        this is needed to grep the correct Ground Truth entry as the simulation will sometimes create different
        TimeStamps.

        configuring TimeStamp synchronisation in .cfg:

    .. python::
            ("SilSilSyncConfig", {    "EnableFrameConversion": True,
                                      "SilSyncSignalName" : "ALGO.AlgoOutput.sSigHeader.uiMeasurementCounter"})
    ..

        This will result in a signal 'AbsoluteTimestamp' on the data bus
        that can be used to find the labels for the 'CurrentSimFile'.

        In case no matching TimeStamp can be found for one frame the AbsoluteTimestamp signal
        will be set to 'None' for that frame.

        The older TimeStamp synchronisation using the Image TimeStamp is still available using the data port:

    .. python::
            ("SilSilSyncConfig", {'EnableTimeConversion': True,
                                  'SilSyncSignalName' : 'SIM VFB.FSD.FsdFanModelData.sSignalHeader.uiTimeStamp'})
    ..

        "EnableFrameConversion" is prioritised, so If both Conversion ports are set to True the Frame Conversion
        is used.

        Find more details about time stamp synchronisation in the .ppt files "Algo_Validation_training"
        and "Timestamps for camera" at the Validatoin sharepoint
        https://cws1.conti.de/content/00012124 in -> Trainings -> VALF_ValidationFramework


        Output port has to be defined in the validation config file.

    """
    def __init__(self, data_manager, component_name, bus_name):
        """init the needed

        :param data_manager: object instance of valf data manager
        :type data_manager: instance
        :param component_name: name used in logging to mark output of this class
        :type component_name: string
        :param bus_name: name of output port in data manager, used to store signals
        :type bus_name: string
        """
        bci.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.7 $")

        # Set up the bin reader.
        self._sig_read = None

        # Object counts
        self.__radar_obj_count = 0  # 40 in ARS301
        self.__ooi_obj_count = 0  # 6 in ARS301
        self.__ibeo_obj_length = 0
        self.__sod_obj_length = 0
        self.__ibeo_obj_count_signal_name = 0
        self.__ibeo_obj_count_port_name = 0
        self.__sod_obj_count_signal_name = 0
        self.__sod_obj_count_port_name = 0

        # Signal port and name lists from config file.
        self.__obj_port_and_signal_names = []
        self.__obj_port_and_signal_names_expanded = []  # pylint: disable=C0103
        self.__ooi_port_and_signal_names = []
        self.__ooi_port_and_signal_names_expanded = []  # pylint: disable=C0103
        self.__fct_port_and_signal_names = []
        self.__vdy_port_and_signal_names = []
        self.__ibeo_obj_port_and_signal_names = []  # pylint: disable=C0103
        self.__ibeo_obj_port_and_signal_names_expanded = []  # pylint: disable=C0103
        self.__sod_obj_port_and_signal_names = []
        self.__sod_obj_port_and_signal_names_expanded = []  # pylint: disable=C0103
        self.__addit_port_and_signal_names = []
        self.__const_port_and_signal_names = []

        # Port names
        self.__obj_port_names = []
        self.__ooi_port_names = []
        self.__ibeo_obj_port_names = []
        self.__sod_obj_port_names = []

        # Data
        self.__objects_list = []
        self.__ooi_obj_list = {}
        self.__ibeo_objects_list = []
        self.__sod_objects_list = []
        self.__inner_gen_obj_list = []

        # Others
        self.__object_id = 0
        self.__ibeo_object_id = 0
        self.__rel_obj_id = []
        self.__extractor_configuration = {}
        self.__obj_min_lifetime = 0
        self.__permitted_empty_signals = None

        # time stamp conversion settings from config file
        self.__use_hil_tmstmp = False
        self.__hil_config = None
        self.__use_sil_sync = None
        self.__sil_config = None

        # AdditionalObjectList
        self.__aol = None

    # --- Framework functions. --------------------------------------------------
    def Initialize(self):  # pylint: disable=R0912
        """
        Read ports OBJ_min_lifetime and SignalExtractorConfig if defined in config, using default values otherwise.
        Initializes ports for signal objects and additional signals as defined.

        default values:

          - 'OBJ_min_lifetime':10
          - 'EnableOBJList'   :False,
          - 'EnableOOIList'   :False,
          - 'EnableFCTData'   :False,
          - 'EnableVDYData'   :False,
          - 'DataSource'      :1
          - 'PermittedEmptySignals': None

        """
        self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")

        with_objs = False

        # Read PORT_NAME_EXTRACTOR_CONFIG
        self.__extractor_configuration = self._data_manager.get_data_port(PORT_NAME_EXTRACTOR_CONFIG, self._bus_name)
        if self.__extractor_configuration is None:
            self._logger.info("The port '%s' is not defined. Using default configuration."
                              % PORT_NAME_EXTRACTOR_CONFIG)
            self.__extractor_configuration = DEFAULT_SIGNAL_EXTRACTOR_CONFIGURATION

        # read PermittedEmptySignals and check for correct type
        if self._data_manager.exists_data_port(PORT_NAME_PERMITTED_EMPTY_SIGNALS, self._bus_name):
            self.__permitted_empty_signals = self.__GetDataPort(PORT_NAME_PERMITTED_EMPTY_SIGNALS, list, str)

        # Initialise additional signal list.
        if self._data_manager.exists_data_port(PORT_NAME_ADDIT_SIGNALS, self._bus_name):
            self.__addit_port_and_signal_names = self.__GetDataPort(PORT_NAME_ADDIT_SIGNALS, list, dict)
        # Get additional port and signal names.
        if self._data_manager.exists_data_port(PORT_NAME_CONST_SIGNALS, self._bus_name):
            self.__const_port_and_signal_names = self.__GetDataPort(PORT_NAME_CONST_SIGNALS, list, dict)

        # Initialize ObjectList, OOIList, FCTData, VDYData.
        if 'EnableOBJList' in self.__extractor_configuration and self.__extractor_configuration['EnableOBJList']:
            self._init_object_list()
            with_objs = True
        if 'EnableOOIList' in self.__extractor_configuration and self.__extractor_configuration['EnableOOIList']:
            self._init_ooi_list()
            with_objs = True
        if 'EnableFCTData' in self.__extractor_configuration and self.__extractor_configuration['EnableFCTData']:
            self._init_fct()
            with_objs = True
        if 'EnableVDYData' in self.__extractor_configuration and self.__extractor_configuration['EnableVDYData']:
            self._init_vdy()
            with_objs = True
        if 'EnableIBEOList' in self.__extractor_configuration and self.__extractor_configuration['EnableIBEOList']:
            self._init_ibeo_list()
            with_objs = True
        if 'EnableSODList' in self.__extractor_configuration and self.__extractor_configuration['EnableSODList']:
            self._init_sod_list()
            with_objs = True

        if with_objs:
            # Get the min object lifetime.
            self.__obj_min_lifetime = self._data_manager.get_data_port(PORT_NAME_OBJ_MIN_LIFETIME, self._bus_name)
            if self.__obj_min_lifetime is None:
                # Keep the default.
                self.__obj_min_lifetime = OBJ_MIN_LIFETIME_DEFAULT
                self._logger.info("Port '%s' not defined, using default value '%s'." %
                                  (self.__obj_min_lifetime, PORT_NAME_OBJ_MIN_LIFETIME))
            elif not isinstance(self.__obj_min_lifetime, int):
                self._logger.exception("'%s' not set to an integer value!")
                sexit(sig_gd.RET_VAL_ERROR)
        # check if SignalExtractor is configured correctly:
        elif not self.__addit_port_and_signal_names and not self.__const_port_and_signal_names:
            self._logger.exception("No signals defined to be read by SignalExtractor. Complete SignalExtractor config!")
            sexit(sig_gd.RET_VAL_ERROR)

        self.__hil_config = self._data_manager.get_data_port(PORT_NAME_HIL_CONFIG, self._bus_name)
        self.__sil_config = self._data_manager.get_data_port(PORT_NAME_SIL_SYNC_CONFIG, self._bus_name)

        if self._init_hil_sync() is not sig_gd.RET_VAL_OK:
            return sig_gd.RET_VAL_ERROR

        if self.__sil_config is not None:
            if ENABLE_FRAME_CONVERSION in self.__sil_config:
                if self.__sil_config[ENABLE_FRAME_CONVERSION] is True:
                    self.__use_sil_sync = SIL_SYNC_VIA_FI
                    self._logger.info('SIL FrameID conversion activated')
            elif ENABLE_TIME_CONVERSION in self.__sil_config:
                if self.__sil_config[ENABLE_TIME_CONVERSION] is True:
                    self.__use_sil_sync = SIL_SYNC_VIA_TS
                    self._logger.info('SIL time stamp conversion activated')

            if SIL_SYNC_SIGNAL not in self.__sil_config:
                self._logger.error("SIL synchronisation settings wrong, missing value for %s" % SIL_SYNC_SIGNAL)
                return sig_gd.RET_VAL_ERROR

        return sig_gd.RET_VAL_OK

    def LoadData(self):  # pylint: disable=R0911,R0912,R0915
        """
        extracting signals as defined in config, sending to given ports with defined names

        LoadData checks existence of bsig reader,
        it can log execution time if SPEED_TEST set to True
        """
        self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")
        if self.__aol is not None:
            safe_cleanup = SafeGuard(self.__aol.clear_cache)

        try:
            # Get the current simulation file.
            current_sim_file = str(self._data_manager.get_data_port("CurrentSimFile", self._bus_name))
            if current_sim_file is None:
                self._logger.error("The port 'CurrentSimFile' is not available.")
                return sig_gd.RET_VAL_ERROR

            self._logger.info("Reading signal values from '%s'. Please wait..." % current_sim_file)
            try:
                if self.__permitted_empty_signals is None:
                    self._sig_read = SignalReader(current_sim_file, use_numpy=False)
                else:
                    self._sig_read = SigExtrReader(current_sim_file, self.__permitted_empty_signals, use_numpy=False)
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                return sig_gd.RET_VAL_ERROR

            if SPEED_TEST is True:
                processing_time_start = time.time()
                self._logger.info("Starting processing ...\n")

            # Load additional signal list. Must contain "MTS.Package.TimeStamp" signal.
            self.__LoadAdditionalSignalList()
            self.__LoadConstSignalList()

            if 'EnableOBJList' in self.__extractor_configuration and self.__extractor_configuration['EnableOBJList']:
                self._load_data_list()
            # Load OOI list. Only works if object list is loaded.
            if 'EnableOOIList' in self.__extractor_configuration and self.__extractor_configuration['EnableOOIList']:
                self._load_data_ooi_list()
            if 'EnableFCTData' in self.__extractor_configuration and self.__extractor_configuration['EnableFCTData']:
                self._load_data_fct()
            if 'EnableVDYData' in self.__extractor_configuration and self.__extractor_configuration['EnableVDYData']:
                self._load_data_vdy()
            if 'EnableIBEOList' in self.__extractor_configuration and self.__extractor_configuration['EnableIBEOList']:
                self._load_ibeo_object_list()
            if 'EnableSODList' in self.__extractor_configuration and self.__extractor_configuration['EnableSODList']:
                self._load_sod_signal_list()

            if SPEED_TEST is True:
                processing_time_end = time.time()
                self._logger.info("Total processing time: %f .\n" % (processing_time_end - processing_time_start))

            # Close the binary signal reader.
            self._sig_read.close()

            ###################################
            # replacing time stamp signal for HIL output
            #
            # the original time stamps can replace the new time stamps if there is
            # a file in bsig format with original time stamps named as configured
            #   - needs original time stamp values and s_EmbeddedRegData.ui64_FrameTimestamp_us
            #     to check synchronisation
            #
            # !! in case of dropped frames in HIL output validation will continue with warnings !!
            #
            ###################################
            if self.__use_hil_tmstmp is True:
                current_tmstmp_file = path.splitext(current_sim_file)[0] + '.' + self.__hil_config[ORI_TIME_FILE_EXT]
                self._logger.info("replacing time stamps with values from %s" % current_tmstmp_file)
                if path.exists(current_tmstmp_file):
                    if self.__replace_timestamps(current_tmstmp_file,
                                                 self.__hil_config[SYNC_SIGNAL],
                                                 self.__hil_config[ORI_TIME_SIGNAL],
                                                 self.__hil_config[HIL_TIME_SIGNAL]) is not sig_gd.RET_VAL_OK:
                        return sig_gd.RET_VAL_ERROR
                else:
                    self._logger.error("HIL time stamp file %s not found/not readable" % current_tmstmp_file)
                    return sig_gd.RET_VAL_ERROR

            if self.__use_sil_sync is not None:
                current_file = str(self._data_manager.get_data_port('CurrentFile', 'Global'))
                current_file_name = path.basename(current_file)
                sim_file_ext = str(self._data_manager.get_data_port('SimFileExt', self._bus_name))
                # time stamp file should be named like: <full_path>\Continuous_2012.05.09_at_05.22.47_tstp.bsig
                current_sil_tmstmp_file = path.dirname(current_sim_file) + '\\'
                current_sil_tmstmp_file += path.splitext(current_file_name)[0] + '_tstp.' + sim_file_ext
                self._logger.info("replacing time stamps with values from %s" % current_sil_tmstmp_file)
                if path.exists(current_sil_tmstmp_file):
                    if self.__use_sil_sync == SIL_SYNC_VIA_FI \
                        and self.__replace_meas_counter(current_sil_tmstmp_file,
                                                        current_sim_file,
                                                        self.__sil_config[SIL_SYNC_SIGNAL]) is not sig_gd.RET_VAL_OK:
                        return sig_gd.RET_VAL_ERROR
                    elif self.__use_sil_sync == SIL_SYNC_VIA_TS \
                        and self.__replace_sil_timestamps(current_sil_tmstmp_file,
                                                          current_sim_file,
                                                          self.__sil_config[SIL_SYNC_SIGNAL]) is not sig_gd.RET_VAL_OK:
                        return sig_gd.RET_VAL_ERROR
                else:
                    self._logger.error("The path to %s does not exist" % current_sil_tmstmp_file)
                    return sig_gd.RET_VAL_ERROR
        finally:
            if self.__aol is not None:
                del safe_cleanup

        return sig_gd.RET_VAL_OK

    def PostProcessData(self):
        """ PostProcessData. Called for each file.
        setting ports to 'None', clears internal object lists
        """
        self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")

        # Set the data ports and signals to None.
        if 'EnableOBJList' in self.__extractor_configuration and self.__extractor_configuration['EnableOBJList']:
            self._data_manager.set_data_port(sig_gd.OBJECT_PORT_NAME, None, self._bus_name)
            self.__objects_list = []
        if 'EnableOOIList' in self.__extractor_configuration and self.__extractor_configuration['EnableOOIList']:
            self._data_manager.set_data_port(sig_gd.OOI_OBJECT_PORT_NAME, None, self._bus_name)
            self.__ooi_obj_list = {}
        if 'EnableFCTData' in self.__extractor_configuration and self.__extractor_configuration['EnableFCTData']:
            self._data_manager.set_data_port(sig_gd.FCTDATA_PORT_NAME, None, self._bus_name)
        if 'EnableVDYData' in self.__extractor_configuration and self.__extractor_configuration['EnableVDYData']:
            self._data_manager.set_data_port(sig_gd.VDYDATA_PORT_NAME, None, self._bus_name)
        if 'EnableIBEOList' in self.__extractor_configuration and self.__extractor_configuration['EnableIBEOList']:
            self._data_manager.set_data_port(sig_gd.IBEO_OBJECT_PORT_NAME, None, self._bus_name)
        if 'EnableSODList' in self.__extractor_configuration and self.__extractor_configuration['EnableSODList']:
            for addit_port_and_signal_name in self.__sod_obj_port_and_signal_names_expanded:
                self._data_manager.set_data_port(addit_port_and_signal_name[PORT_NAME], None, self._bus_name)

        for port in self.__addit_port_and_signal_names:
            self._data_manager.set_data_port(port[PORT_NAME], None, self._bus_name)

        for port in self.__const_port_and_signal_names:
            self._data_manager.set_data_port(port[PORT_NAME], None, self._bus_name)

        unreachable_objects = collect()
        if unreachable_objects != 0:
            self._logger.info("Unreachable objects for garbage collector. %d" % unreachable_objects)

        return sig_gd.RET_VAL_OK

    # --- Module functions. Initialize. --------------------------------------------------
    def _init_object_list(self):
        """
        initialise general signal objects list, create __obj_port_names for each object as:

        [{ 'PortName': <PortName>#, 'Count': #, 'SignalName': <Prefix>+<SignalName>+# } ...]

        using ports
          - OBJ_Prefix,
          - OBJ_Length,
          - OBJ_Count,
          - OBJ_Signals with SignalName and PortName

        """
        # Get the prefix for the OBJ signals.
        obj_name_prefix = self.__GetDataPort(PORT_NAME_OBJ_PREFIX, str, None)
        # Get the number of OBJ objects.
        self.__radar_obj_count = self.__GetDataPort(PORT_NAME_OBJ_COUNT, int, None)
        # Get OBJ port and signal names.
        self.__obj_port_and_signal_names = self.__GetDataPort(PORT_NAME_OBJ_SIGNALS, list, dict, True)

        # additional object signals
        add_obj_mapping_rule = self._data_manager.get_data_port(PORT_NAME_ADD_OBJ_MAP, self._bus_name)
        add_obj_list_size = self._data_manager.get_data_port(PORT_NAME_ADD_OBJ_LIST_SIZE, self._bus_name)
        if add_obj_mapping_rule is not None and add_obj_list_size is not None:
            add_obj_port_and_signal_names = self.__GetDataPort(PORT_NAME_ADD_OBJ_SIGNALS, list, dict, True)
            add_obj_prefix = self._data_manager.get_data_port(PORT_NAME_ADD_OBJ_PREFIX, self._bus_name)
            self.__aol = AdditionalObjectList(self._sig_read, add_obj_mapping_rule, add_obj_port_and_signal_names,
                                              add_obj_list_size, add_obj_prefix)
        # Update the signals with prefixes.
        for object_index in range(self.__radar_obj_count):
            for obj_port_and_signal_name in self.__obj_port_and_signal_names:
                obj_expanded = {PORT_NAME: obj_port_and_signal_name[PORT_NAME] + str(object_index),
                                COUNT: str(object_index),
                                SIGNAL_NAME: (obj_name_prefix + obj_port_and_signal_name[SIGNAL_NAME])
                                .replace("%", '%(iIndex)d' % {'iIndex': object_index})}
                self.__obj_port_and_signal_names_expanded.append(obj_expanded)

        # Create a list of port names only.
        self.__obj_port_names = self.GetListFromDictList(self.__obj_port_and_signal_names, PORT_NAME)

    def _init_ooi_list(self):
        """
        initialise OOI signal objects list, create __ooi_port_names as

        [{ 'PortName': <PortName>#, 'Count': #, 'SignalName': <Prefix>+<SignalName>+# } ...]

        using ports
          - OOI_Prefix,
          - OOI_number_of_objects,
          - OOI_signals with SignalName and PortName

        """
        # Get the prefix for the OOI signals.
        ooi_name_prefix = self.__GetDataPort(PORT_NAME_OOI_PREFIX, str, None)
        # Get the number of OOI objects.
        self.__ooi_obj_count = self.__GetDataPort(PORT_NAME_OOI_COUNT, int, None)
        # Get OOI port and signal names.
        self.__ooi_port_and_signal_names = self.__GetDataPort(PORT_NAME_OOI_SIGNALS, list, dict, True)
        # Generate the urls for the OOI list.
        for ooi_index in range(self.__ooi_obj_count):
            for index, ooi_port_and_signal_name in enumerate(self.__ooi_port_and_signal_names):
                snm = (ooi_name_prefix +
                       self.__ooi_port_and_signal_names[index][SIGNAL_NAME]).replace("%", '%(iIndex)d'
                                                                                     % {'iIndex': ooi_index})
                ooi_port_and_signal_name_expanded = {PORT_NAME: ooi_port_and_signal_name[PORT_NAME] + str(ooi_index),
                                                     COUNT: str(ooi_index), SIGNAL_NAME: snm}
                self.__ooi_port_and_signal_names_expanded.append(ooi_port_and_signal_name_expanded)

        # Create a list of port names only.
        self.__ooi_port_names = self.GetListFromDictList(self.__ooi_port_and_signal_names, PORT_NAME)

    def _init_fct(self):
        """ Initialise the FCT data. """
        # Get the prefix for the FCT signals.
        fct_name_prefix = self.__GetDataPort(PORT_NAME_FCT_PREFIX, str, None)
        # Get FCT port and signal names.
        self.__fct_port_and_signal_names = self.__GetDataPort(PORT_NAME_FCT_SIGNALS, list, dict, True)
        # Update the signals with prefixes.
        for fct_port_signal_data in self.__fct_port_and_signal_names:
            fct_port_signal_data[SIGNAL_NAME] = fct_name_prefix + fct_port_signal_data[SIGNAL_NAME]

    def _init_vdy(self):
        """ Initialise the VDY data. """
        # Get the preffix for the VDY signals.
        vdy_name_prefix = self.__GetDataPort(PORT_NAME_VDY_PREFIX, str, None)
        # Get VDY port and signal names.
        self.__vdy_port_and_signal_names = self.__GetDataPort(PORT_NAME_VDY_SIGNALS, list, dict, True)
        # Update the signals with prefixes.
        for vdy_port_signal_data in self.__vdy_port_and_signal_names:
            vdy_port_signal_data[SIGNAL_NAME] = vdy_name_prefix + vdy_port_signal_data[SIGNAL_NAME]

    def _init_ibeo_list(self):
        """
        initialise ibeo signal objects list, create __ibeo_obj_port_names for each object as:

        [{ 'PortName': <PortName>#, 'Count': #, 'SignalName': <Prefix>+<SignalName>+# } ...]

        using ports
          - IbeoOut_Prefix,
          - IbeoOut_Length,
          - IbeoOut_Count,
          - IbeoOut_ObjSignals with SignalName and PortName
        """
        # Get the prefix for the OBJ signals.
        obj_name_prefix = self.__GetDataPort(PORT_NAME_IBEO_OBJ_PREFIX, str, None)
        # Get total the number of Ibeo objects.
        self.__ibeo_obj_length = self.__GetDataPort(PORT_NAME_IBEO_OBJ_LENGTH, int, None)
        # Get the actual number of objects
        self.__ibeo_obj_count_signal_name = obj_name_prefix + self.__GetDataPort(PORT_NAME_IBEO_OBJ_COUNT, str, None)
        self.__ibeo_obj_count_port_name = self.__GetDataPort(PORT_NAME_IBEO_OBJ_COUNT, str, None)

        # Get OBJ port and signal names.
        self.__ibeo_obj_port_and_signal_names = self.__GetDataPort(PORT_NAME_IBEO_OBJ_SIGNALS, list, dict, True)
        # Update the signals with prefixes.
        for object_index in range(self.__ibeo_obj_length):
            for obj_port_and_signal_name in self.__ibeo_obj_port_and_signal_names:
                snm = (obj_name_prefix +
                       obj_port_and_signal_name[SIGNAL_NAME]).replace("%", '%(iIndex)d' % {'iIndex': object_index})
                obj_port_and_signal_name_expanded = {PORT_NAME: obj_port_and_signal_name[PORT_NAME] + str(object_index),
                                                     COUNT: str(object_index), SIGNAL_NAME: snm}
                self.__ibeo_obj_port_and_signal_names_expanded.append(obj_port_and_signal_name_expanded)

        # Create a list of port names only.
        self.__ibeo_obj_port_names = self.GetListFromDictList(self.__ibeo_obj_port_and_signal_names, PORT_NAME)

    def _init_sod_list(self):
        """
        initialise sod signal objects list, create __sod_obj_port_names for each object as:

        [{ 'PortName': <PortName>#, 'Count': #, 'SignalName': <Prefix>+<SignalName>+# } ...]

        using ports
          - SODOut_Prefix,
          - SODOut_Length,
          - SODOut_Count,
          - SODOut_ObjSignals with SignalName and PortName

        :returns: nothing
        """
        # Get the prefix for the OBJ signals.
        obj_name_prefix = self.__GetDataPort(PORT_NAME_SOD_OBJ_PREFIX, str, None)
        # Get total the number of SOD objects.
        self.__sod_obj_length = self.__GetDataPort(PORT_NAME_SOD_OBJ_LENGTH, int, None)

        # Get the actual number of objects
        # self.__sod_obj_count_signal_name = obj_name_prefix + self.__GetDataPort(PORT_NAME_SOD_OBJ_COUNT, str, None)
        # self.__sod_obj_count_port_name   = self.__GetDataPort(PORT_NAME_SOD_OBJ_COUNT, str, None)

        # Get OBJ port and signal names.
        self.__sod_obj_port_and_signal_names = self.__GetDataPort(PORT_NAME_SOD_OBJ_SIGNALS, list, dict, True)
        # Update the signals with prefixes (for sod maximum is 40 object, set to 40 object all signals and ports)
        for object_index in xrange(40 if self.__sod_obj_length == 0 else self.__sod_obj_length):
            for obj_port_and_signal_name in self.__sod_obj_port_and_signal_names:

                obj_port_and_signal_name_expanded = {}  # pylint: disable=C0103

                obj_port_and_signal_name_expanded[PORT_NAME] = obj_port_and_signal_name[PORT_NAME] + str(object_index)
                obj_port_and_signal_name_expanded[COUNT] = str(object_index)
                obj_port_and_signal_name_expanded[SIGNAL_NAME] = \
                    (obj_name_prefix +
                     obj_port_and_signal_name[SIGNAL_NAME]).replace("%", '%(iIndex)d' % {'iIndex': object_index})
                self.__sod_obj_port_and_signal_names_expanded.append(obj_port_and_signal_name_expanded)

        # Create a list of port names only.
        self.__sod_obj_port_names = self.GetListFromDictList(self.__sod_obj_port_and_signal_names, PORT_NAME)

    def _init_hil_sync(self):
        """
        check for HIL timestamp configuration and initialize synchronisation

        control if all mandatory settings are done, set defaults for missing optional settings

        :returns: RET_VAL_OK (0) or RET_VAL_ERROR (-1)
        """
        if self.__hil_config is not None:
            if ENABLE_TIME_CONVERSION in self.__hil_config and self.__hil_config[ENABLE_TIME_CONVERSION] is True:
                # ignore HIL config is HIL is not activated
                self.__use_hil_tmstmp = True
                self._logger.info('HIL time stamp conversion activated')

                # check all HIL config and report all errors at once
                # file extension for bsig file with original time stamps
                if ORI_TIME_FILE_EXT not in self.__hil_config:
                    self.__hil_config[ORI_TIME_FILE_EXT] = HIL_TMSTAMP_FILE_EXT
                self._logger.info("HIL time stamp files extension set to '%s'"
                                  % self.__hil_config[ORI_TIME_FILE_EXT])
                # mandatory name of original time stamp signal to copy in HIL output
                if ORI_TIME_SIGNAL in self.__hil_config:
                    # optional name of time stamp signal as stored in HIL output, default same as ori. TS signal name,
                    if HIL_TIME_SIGNAL not in self.__hil_config:
                        self.__hil_config[HIL_TIME_SIGNAL] = self.__hil_config[ORI_TIME_SIGNAL]
                        self._logger.info("name of HIL Time signal to change is not set, using same as %s"
                                          % ORI_TIME_SIGNAL)
                else:
                    self._logger.error("HIL Time Stamp settings wrong, missing value for %s" % ORI_TIME_SIGNAL)
                    return sig_gd.RET_VAL_ERROR
                # mandatory name of signal to synch time stamps, should be embedded time stamp signal
                # it should have same values for both files, so only one config needed
                if SYNC_SIGNAL not in self.__hil_config:
                    self._logger.error("HIL Time Stamp settings wrong, missing value for %s" % SYNC_SIGNAL)
                    return sig_gd.RET_VAL_ERROR

            else:
                self._logger.info("no HIL time conversion used, set value '%s' to True to activate"
                                  % ENABLE_TIME_CONVERSION)
        return sig_gd.RET_VAL_OK

    # --- Module functions. LoadData. --------------------------------------------------
    def _load_data_list(self):  # pylint: disable=C0103
        """ Load the object list.
        """
        # Get the relevant object data from the additional signals list.
        self.__rel_obj_id = self._data_manager.get_data_port(PORT_NAME_REL_OBJ_ID, self._bus_name)

        # Set the default relevant index for the first cycles.
        for idx in range(min(IGNORE_OOI_FIRST_CYCLES, len(self.__rel_obj_id))):
            self.__rel_obj_id[idx] = INVALID_OBJECT[0]

        # Load the object list.
        if self._data_manager.get_data_port(PORT_NAME_OBJ_GENERIC_LIST, self._bus_name):
            # as generic object list
            self._logger.info("Extracting objects as generic object list")

            self.__inner_gen_obj_list = []
            for col_idx in range(self.__radar_obj_count):
                self._load_data_object(col_idx)

            generic_obj_list = GenericObjectList(self._data_manager, "ARS4xx", "ObjectList", None,
                                                 self._bus_name, objects=self.__inner_gen_obj_list)
            self._data_manager.set_data_port(sig_gd.OBJECT_PORT_NAME, generic_obj_list, self._bus_name)
        else:
            # Classic as list of dictionary
            self.__objects_list = []
            self.__object_id = 0

            for col_idx in range(self.__radar_obj_count):
                self._load_data_object(col_idx)

            # Sort the object list based on the timestamp.
            self.__objects_list.sort(lambda x, y: cmp(int(x["StartTime"]), int(y["StartTime"])))
            self._data_manager.set_data_port(sig_gd.OBJECT_PORT_NAME, self.__objects_list, self._bus_name)

    def _load_data_object(self, col_index):  # pylint: disable=C0103
        """ Load the data for one object.

        :param col_index: The index (0-39 for ARS301)
        """
        done = False
        last_pos = 0
        signal_data_list = []

        # To generate the object list, port ucLifeTime is required as the first signal.
        if self.__obj_port_names[0] == PORT_NAME_EOBJMAINTENANCESTATE:
            self._logger.debug("Using signal 'eObjMaintenanceState' for object separation.")
            scanner = self.__ScanColumn2
        elif self.__obj_port_names[0] == PORT_NAME_UILIFETIME:
            self._logger.info("Using legacy signal 'uiLifeTime', " +
                              "consider using signal 'eObjMaintenanceState' instead.")
            scanner = self.__ScanColumn
        else:
            self._logger.error("Need to place signal 'eObjMaintenanceState' " +
                               "or 'uiLifeTime' signal as first signal in the OBJ list in the config file.")
            sexit(sig_gd.RET_VAL_ERROR)

        # Load the lifetime signal.
        obj_signal_urls = self.GetListFromDictList(self.__obj_port_and_signal_names_expanded, SIGNAL_NAME)

        sig_name_uilifetime = obj_signal_urls[col_index * len(self.__obj_port_names)]
        try:
            ui_life_time_data = self._sig_read[sig_name_uilifetime]
        except SignalReaderException as ex:
            self._logger.error(str(ex))
            sexit(sig_gd.RET_VAL_ERROR)

        # Load all the OBJ signals.
        for obj_port_name_idx in range(len(self.__obj_port_names)):
            try:
                sig_name = obj_signal_urls[obj_port_name_idx + col_index * len(self.__obj_port_names)]
                signal_data_list.append(self._sig_read[sig_name])
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                sexit(sig_gd.RET_VAL_ERROR)

        # Distinguish between Generic Object List and classic llist of dict
        if self._data_manager.get_data_port(PORT_NAME_OBJ_GENERIC_LIST, self._bus_name):
            extractor = self.__ExtractObjectData2
        else:
            extractor = self.__ExtractObjectData

        # Extract objects.
        while not done:
            object_position = scanner(ui_life_time_data, last_pos)
            if object_position is not None:
                last_pos = object_position[0] + object_position[1]
                extractor(col_index, signal_data_list, object_position[0], object_position[1])
            else:
                done = True

    def _load_data_ooi_list(self):  # pylint: disable=R0912,R0914,R0915
        """ Load the OOI data list.
        """
        self.__ooi_obj_list = {}

        # Load the OOI list.
        for ooi_index in range(self.__ooi_obj_count):
            object_name = 'OOIObject[' + str(ooi_index) + ']'
            self.__ooi_obj_list[object_name] = []

            # Read the signal data for an OOI from the binary file.
            ooi_signal_data = []
            first_b = True
            for ooi_port_and_signal_name_expanded in self.__ooi_port_and_signal_names_expanded:  # pylint: disable=C0103
                if ooi_port_and_signal_name_expanded[COUNT] == str(ooi_index):
                    try:
                        if first_b:
                            first_b = False
                            sig_data = self._sig_read[ooi_port_and_signal_name_expanded[SIGNAL_NAME]]

                        sig_data2 = self._sig_read[ooi_port_and_signal_name_expanded[SIGNAL_NAME]]
                        ooi_signal_data.append(sig_data2)

                    except SignalReaderException as ex:
                        self._logger.error(str(ex))
                        sexit(sig_gd.RET_VAL_ERROR)

            # Generate OOI object list.
            current_pos = IGNORE_OOI_FIRST_CYCLES
            bnewobject = False
            # Process the object_id data.
            while current_pos < len(sig_data):
                # If the object id is -1 then skip to the next object id.
                if sig_data[current_pos] in INVALID_OBJECT:
                    current_pos += 1
                else:
                    # Get the current ooi id.
                    current_obj_id = sig_data[current_pos]
                    # Set the starting positing and start length of the ooi.
                    start_pos = current_pos
                    length = 0
                    # Move along the data until the ooi id changes.
                    while (current_obj_id == sig_data[current_pos]) and (current_pos < len(sig_data) - 1):
                        current_pos += 1
                        length += 1
                    # The end of the ooi has been reached.
                    object_column = None
                    if length >= 1:
                        bnewobject = True
                        object_column = {}
                        for name in self.__ooi_port_names:
                            ind = self.__ooi_port_names.index(name)
                            if ooi_signal_data[ind]:
                                object_column[name] = ooi_signal_data[ind][start_pos:start_pos + length]
                        object_column["start_index"] = start_pos
                        object_column["stop_index"] = start_pos + length
                    else:
                        current_pos += 1

                    # Complete processing of new ooi.
                    if bnewobject is True:
                        bnewobject = False
                        matching_obj = None
                        match_obj_index = 0
                        if object_column is not None:
                            obj_index = 0
                            # Find a matching object in the objects list.
                            for obj in self.__objects_list:
                                if obj['ObjectId'] == object_column['object_id'][0]:
                                    if(object_column["start_index"] >= obj['Index'] and
                                       object_column["stop_index"] <= obj['Index'] + len(obj['Timestamp'])):
                                        matching_obj = obj
                                        match_obj_index = obj_index
                                        break
                                obj_index += 1

                            # Append the matching object data.
                            if matching_obj is not None:
                                matching_obj['OOIHistory'].append({"OOIObjectIndex": ooi_index,
                                                                   "StartIndexAsOOI": start_pos, "Length": length})
                                object_column["obj"] = matching_obj
                                object_column["obj_index"] = match_obj_index
                                self.__ooi_obj_list[object_name].append(object_column)

        for obj in self.__objects_list:
            obj['OOIHistory'].sort(lambda x, y: cmp(int(x['StartIndexAsOOI']), int(y['StartIndexAsOOI'])))

        self._data_manager.set_data_port(sig_gd.OOI_OBJECT_PORT_NAME, self.__ooi_obj_list, self._bus_name)

    def _load_data_fct(self):  # pylint: disable=C0103
        """ Load the FCT data. """
        fct_ports_and_data = self.__LoadBinData(self.__fct_port_and_signal_names)
        self._data_manager.set_data_port(sig_gd.FCTDATA_PORT_NAME, fct_ports_and_data, self._bus_name)

    def _load_data_vdy(self):  # pylint: disable=C0103
        """ Load the VDY data. """
        vdy_ports_and_data = self.__LoadBinData(self.__vdy_port_and_signal_names)
        self._data_manager.set_data_port(sig_gd.VDYDATA_PORT_NAME, vdy_ports_and_data, self._bus_name)

    def _load_ibeo_object_list(self):  # pylint: disable=C0103
        """ Load the object list. """

        self.__ibeo_objects_list = []

        # load the obect counts
        try:
            object_count = self._sig_read[self.__ibeo_obj_count_signal_name]
        except SignalReaderException as ex:
            self._logger.error(str(ex))
            sexit(sig_gd.RET_VAL_ERROR)
        self.__ibeo_objects_list.append(object_count)

        for col_idx in range(self.__ibeo_obj_length):
            self.__LoadIbeoObject(col_idx)

        self._data_manager.set_data_port(sig_gd.IBEO_OBJECT_PORT_NAME, self.__ibeo_objects_list, self._bus_name)

    def __LoadIbeoObject(self, col_index):  # pylint: disable=C0103
        """ Load the data for one object.

        :param col_index: The index (0-32 for Ibeo)
        """
        signal_data_list = []

        # To generate the object list, port ObjId is required
        if self.__ibeo_obj_port_names[0] != PORT_NAME_IBEO_OBJ_ID:
            self._logger.error("Need to place the object id signal as first signal "
                               "in the Ibeo OBJ list in the config file.")
            sexit(sig_gd.RET_VAL_ERROR)

        # Load the signals .
        obj_signal_urls = self.GetListFromDictList(self.__ibeo_obj_port_and_signal_names_expanded, SIGNAL_NAME)

        sig_name_obj_id = obj_signal_urls[col_index * len(self.__ibeo_obj_port_names)]
        try:
            # SMe: unused object object_ids???
            # object_ids =
            self._sig_read[sig_name_obj_id]
        except SignalReaderException as ex:
            self._logger.error(str(ex))
            sexit(sig_gd.RET_VAL_ERROR)

        # Load all the OBJ signals.
        for obj_port_name_idx in range(len(self.__ibeo_obj_port_names)):
            try:
                sig_name = obj_signal_urls[obj_port_name_idx + col_index * len(self.__ibeo_obj_port_names)]
                obj_signal_data = self._sig_read[sig_name]
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                sexit(sig_gd.RET_VAL_ERROR)

            signal_data_list.append(obj_signal_data)

        # extract the objects
        objects = {}
        for obj_port_name in self.__ibeo_obj_port_names:
            try:
                idx = self.__ibeo_obj_port_names.index(obj_port_name)
                if signal_data_list[idx]:
                    objects[obj_port_name] = signal_data_list[idx]
            except:  # pylint: disable=W0702
                self._logger.error("Error while extracting data for object: %s obj_port_name." % obj_port_name)
                sexit(sig_gd.RET_VAL_ERROR)

        self.__ibeo_objects_list.append(objects)

    def __LoadAdditionalSignalList(self):  # pylint: disable=C0103
        """ Load the additional signals. """
        for addit_port_and_signal_name in self.__addit_port_and_signal_names:
            try:
                signal_data = self._sig_read[addit_port_and_signal_name[SIGNAL_NAME]]
                if signal_data is None:
                    self._logger.debug("There is no data available for %s signal in the binary file." %
                                       addit_port_and_signal_name[SIGNAL_NAME])
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                signal_data = None
                # sys.sexit(sig_gd.RET_VAL_ERROR)
            self._data_manager.set_data_port(addit_port_and_signal_name[PORT_NAME], signal_data, self._bus_name)

    def __LoadConstSignalList(self):  # pylint: disable=C0103
        """
        Load the additional signals.
        For signals where we don't care about the entire timecourse but that we
        assume to be constant, we load the last signal sample.
        """
        for const_port_and_signal_name in self.__const_port_and_signal_names:
            try:
                # just to keep signals as a list for now.
                signal_data = self._sig_read[const_port_and_signal_name[SIGNAL_NAME]:-3:2]
                if signal_data is None:
                    self._logger.debug("There is no data available for %s signal in the binary file." %
                                       const_port_and_signal_name[SIGNAL_NAME])
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                signal_data = None
                # sys.sexit(sig_gd.RET_VAL_ERROR)
            self._data_manager.set_data_port(const_port_and_signal_name[PORT_NAME], signal_data, self._bus_name)

    def _load_sod_signal_list(self):  # pylint: disable=C0103
        """ Load the additional signals. """

        if self.__sod_obj_length == 0:
            max_numb_ob = max(self._data_manager.get_data_port("iNumOfUsedObjects", self._bus_name))
            self._logger.info("max NUMBER-------------------------------%d" % max_numb_ob)
        else:
            max_numb_ob = self.__sod_obj_length

        self._data_manager.set_data_port("MAX_USED_OBJ", max_numb_ob)
        for addit_port_and_signal_name in self.__sod_obj_port_and_signal_names_expanded:
            if int(addit_port_and_signal_name[COUNT]) >= max_numb_ob:
                continue
            try:
                signal_data = self._sig_read[addit_port_and_signal_name[SIGNAL_NAME]]
                if signal_data is None:
                    self._logger.debug("There is no data available for %s signal in the binary file." %
                                       addit_port_and_signal_name[SIGNAL_NAME])
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                signal_data = None
                # sys.sexit(sig_gd.RET_VAL_ERROR)
            self._data_manager.set_data_port(addit_port_and_signal_name[PORT_NAME], signal_data, self._bus_name)

    def __LoadBinData(self, port_and_signal_names):  # pylint: disable=C0103
        """ Load binary data from file.

        :param port_and_signal_names: The port and signal name list.
        :return: Ports and data in the form of a dict.
        """
        ports_and_data = {}
        for port_and_signal_name in port_and_signal_names:
            try:
                data = self._sig_read[port_and_signal_name[SIGNAL_NAME]]
            except SignalReaderException as ex:
                self._logger.error(str(ex))
                sexit(sig_gd.RET_VAL_ERROR)
            ports_and_data[port_and_signal_name[PORT_NAME]] = data
        return ports_and_data

    # --- Helper functions. --------------------------------------------------
    def __ScanColumn(self, ui_life_time_data, start_position):  # pylint: disable=C0103
        """ Scan a column.

        :param ui_life_time_data: The object life time data.
        :param start_position: The start position in the cycle array.
        :return: (new start position, length of object)
        """
        current_pos = start_position
        length = 0
        data_len = len(ui_life_time_data) - 1

        while current_pos < data_len:
            if ui_life_time_data[current_pos] == 0:
                current_pos += 1
            else:
                new_start_position = current_pos
                while (current_pos < data_len and ui_life_time_data[current_pos] != 0 and
                       ui_life_time_data[current_pos] <= ui_life_time_data[current_pos + 1] and
                       ui_life_time_data[current_pos + 1] != 1):
                    length += 1
                    current_pos += 1
                return new_start_position, length + 1
        return None

    def __ScanColumn2(self, maintenance_state, start_position):  # pylint: disable=C0103
        """ Searches for the next start index and duration of the next object.

        :param maintenance_state: Maintenance state signal for the current object lane
        :param start_position: The start position from where to search the next objects
        :returns: Tuple containing start index and life time of the next object.
        """
        # States taken from HeaderFile:
        # MT_STATE_DELETED  (0U)
        # MT_STATE_NEW  (1U)
        # MT_STATE_MEASURED  (2U)
        # MT_STATE_PREDICTED  (3U)
        # MT_STATE_MERGE_DELETED  (4U)
        # MT_STATE_MERGE_NEW  (5U)

        life_time = 0
        for k in range(start_position, len(maintenance_state)):

            if maintenance_state[k] == 1 or maintenance_state[k] == 5:
                if life_time == 0:
                    start_position = k
                    life_time += 1
                    # self._logger.debug("Scanner init {0:}/{1:}".format(start_position, life_time))
                else:
                    # self._logger.debug("Scanner returning {0:}/{1:}".format(start_position, life_time))
                    # value = maintenance_state[start_position - 3: start_position]
                    # self._logger.debug("Stride pre:  {0:}".format(value))
                    # value = maintenance_state[start_position: start_position + life_time]
                    # self._logger.debug("Stride obj:  {0:}".format(value))
                    # value = maintenance_state[start_position + life_time: start_position + life_time + 3]
                    # self._logger.debug("Stride post: {0:}".format(value))
                    return start_position, life_time
            elif maintenance_state[k] == 2 or maintenance_state[k] == 3:
                # self._logger.debug("Scanner advancing {0:}/{1:}".format(start_position, life_time))
                life_time += 1
            elif (maintenance_state[k] == 0 or
                  maintenance_state[k] == 4):
                if life_time != 0:
                    # State deleted
                    return (start_position, life_time)

        if life_time:
            return (start_position, life_time)

        return None

    def __GetDataPort(self, port_name, item_type, subitem_type, check_length=False):  # pylint: disable=C0103
        """ Get the data port.

        :param port_name: The port name (string).
        :param item_type: Eg. int, float, bool, list, tuple
        :param subitem_type: Eg. int, float, bool, list, tuple
        :param check_length: Checks that list element has not 0 length. Default = False.
        """
        data_port = self._data_manager.get_data_port(port_name, self._bus_name)
        # Check if data port is None.
        if data_port is None:
            self._logger.error("The port with the name '%s' was not found." % port_name)
            sexit(sig_gd.RET_VAL_ERROR)
        # Check data port type.
        if not isinstance(data_port, item_type):
            self._logger.error("Expected " + str(item_type) + " type.")
            sexit(sig_gd.RET_VAL_ERROR)

        # If the port type is a list check each of the element of that list.
        if item_type == list and subitem_type is not None:
            for list_element in data_port:
                # Check type for the element.
                if not isinstance(list_element, subitem_type):
                    self._logger.error("There was an error retrieving data for port %s. Expecting a different type."
                                       % port_name)
                    sexit(sig_gd.RET_VAL_ERROR)
                else:
                    # Check the length of the list element.
                    if check_length is True and len(list_element) == 0:
                        self._logger.error("There was an error retrieving data for port %s. Element list length = 0."
                                           % port_name)
                        sexit(sig_gd.RET_VAL_ERROR)
        else:
            # Check the length of the list element.
            if check_length is True and len(data_port):
                self._logger.error("There was an error retrieving data for port %s." % port_name)
                sexit(sig_gd.RET_VAL_ERROR)

        return data_port

    def __ExtractObjectData2(self, object_index, signal_data_list, start_position, length):  # pylint: disable=C0103
        """ Extract object data but will create Generic rect Object and append to
        generic object list.

        :param object_index: The object index.
        :param signal_data_list: List of signal data (the signal data is a list of values).
        :param start_position: The start position.
        :param length: The length in cycles of the object.
        """
        b_is_relevant = False
        self.__object_id += 1

        # Get the timestamp data.
        timestamp = self._data_manager.get_data_port("Timestamp", self._bus_name)
        if len(timestamp) == 0:
            self._logger.error("Timestamp information is not available for bus name %s." % self._bus_name)
            sexit(sig_gd.RET_VAL_ERROR)

        # Calculate the end position.
        end_position = min(len(timestamp) - 1, start_position + length)

        new_obj = {"GlobalObjectId": self.__object_id, "ObjectId": object_index,
                   "StartTime": timestamp[start_position], "Timestamp": timestamp[start_position:end_position],
                   "Index": start_position, "OOIHistory": [], "Relevant": [], "fDistXAbs": [], "fDistYAbs": []}

        for obj_port_name in self.__obj_port_names:
            obj_index = self.__obj_port_names.index(obj_port_name)
            try:
                # new_obj[obj_port_name] = signal_data_list[obj_index][start_position:start_position + length]
                if signal_data_list[obj_index]:
                    new_obj[obj_port_name] = signal_data_list[obj_index][start_position:end_position]
            except:  # pylint: disable=W0702
                self._logger.error("Error while extracting data for object: %s obj_port_name." % obj_port_name)
                sexit(sig_gd.RET_VAL_ERROR)

        for pos in range(start_position, end_position):
            if self.__rel_obj_id[pos] == object_index:
                new_obj["Relevant"].append(1)
                b_is_relevant = True
            else:
                new_obj["Relevant"].append(0)

        # object was not already classified as being relevant at some point
        # find out if object is selected as OOI 1 to 5 at some point
        if (b_is_relevant is False) and (new_obj.get("ObjOOI") is not None):
            for ooi_idx in new_obj["ObjOOI"]:
                if ooi_idx > -1:
                    b_is_relevant = True
                    break

        if b_is_relevant or length > self.__obj_min_lifetime:
            # self.__objects_list.append(new_obj)
            # Ugly as hell
            gen_rect_obj = GenericRectObject(self.__object_id, object_index,
                                             timestamp[start_position],
                                             timestamp[end_position],
                                             self._data_manager, self._bus_name,
                                             signal_names=self.__obj_port_names,
                                             obj=new_obj)
            self.__inner_gen_obj_list.append(gen_rect_obj)
        else:
            pass

    def __ExtractObjectData(self, object_index, signal_data_list, start_position,  # pylint: disable=C0103,R0912
                            length):  # pylint: disable=R0912
        """ Extract object data.

        :param object_index: The object index.
        :param signal_data_list: List of signal data (the signal data is a list of values).
        :param start_position: The start position.
        :param length: The length in cycles of the object.
        """
        b_is_relevant = False
        self.__object_id += 1

        # Get the timestamp data.
        timestamp = self._data_manager.get_data_port("Timestamp", self._bus_name)
        if len(timestamp) == 0:
            self._logger.error("Timestamp information is not available for bus name %s." % self._bus_name)
            sexit(sig_gd.RET_VAL_ERROR)

        # Calculate the end position.
        end_position = min(len(timestamp) - 1, start_position + length)

        new_obj = {"GlobalObjectId": self.__object_id, "ObjectId": object_index,
                   "StartTime": timestamp[start_position], "Timestamp": timestamp[start_position:end_position],
                   "Index": start_position, "OOIHistory": [], "Relevant": [], "fDistXAbs": [], "fDistYAbs": []}

        for obj_port_name in self.__obj_port_names:
            obj_index = self.__obj_port_names.index(obj_port_name)
            try:
                # new_obj[obj_port_name] = signal_data_list[obj_index][start_position:start_position + length]
                if signal_data_list[obj_index]:
                    new_obj[obj_port_name] = signal_data_list[obj_index][start_position:end_position]
            except:  # pylint: disable=W0702
                self._logger.error("Error while extracting data for object: %s obj_port_name." % obj_port_name)
                sexit(sig_gd.RET_VAL_ERROR)

        # add additional object signals
        if self.__aol is not None:
            mapping_successful = self.__aol.add_additional_object_signals(new_obj, object_index, start_position,
                                                                          end_position, self._sig_read)

        for pos in range(start_position, end_position):
            if self.__rel_obj_id[pos] == object_index:
                new_obj["Relevant"].append(1)
                b_is_relevant = True
            else:
                new_obj["Relevant"].append(0)

        # object was not already classified as being relevant at some point
        # find out if object is selected as OOI 1 to 5 at some point
        if (b_is_relevant is False) and (new_obj.get("ObjOOI") is not None):
            for ooi_idx in new_obj["ObjOOI"]:
                if ooi_idx > -1:
                    b_is_relevant = True
                    break

        if b_is_relevant or length > self.__obj_min_lifetime:
            if self.__aol is not None:
                if mapping_successful:
                    self.__objects_list.append(new_obj)
            else:
                self.__objects_list.append(new_obj)
        else:
            pass

    def __replace_sil_timestamps(self, current_sil_file, current_file, sync_signal_name):
        r"""
        replace the uiTimestamp from the sync_signal_name from current_file with the AbsoluteTimestamp
        from current_sil_file (the _tspt.bsig file)

        :param current_sil_file: path & filename of \*_tstp.bsig with uiTimeStamp and signals to synchronise it
        :type current_sil_file: string
        :param current_file: path and filename of \*.bsig file with all simulation output
        :type current_file:  string
        :param sync_signal_name: name of signal in sim output to synchronise to time stamp
        :type sync_signal_name:  string
        """
        sil_ts = []
        with SignalReader(current_file) as reader:
            sync_ts = reader[sync_signal_name].tolist()

        with SignalReader(current_sil_file) as reader:
            abs_ts = reader[SIL_TS_ABSOLUTE_TS].tolist()
            img_ts = reader[SIL_IMAGE_TS].tolist()

        for i in range(len(sync_ts)):
            found = False

            for k in range(50):
                candidates = []

                if 0 <= i - k < len(img_ts):
                    candidates.append(i - k)

                if k != 0 and 0 <= i + k < len(img_ts):
                    candidates.append(i + k)

                for j in candidates:
                    if img_ts[j] != 0 and (img_ts[j] & 0xFFFFFFFF) == (sync_ts[i] & 0xFFFFFFFF):
                        sil_ts.append(abs_ts[j])
                        found = True
                        break
                if found:
                    break

            if not found:
                sil_ts.append(None)

        self._data_manager.set_data_port(SIL_SYNC_TS, sil_ts, self._bus_name)
        return sig_gd.RET_VAL_OK

    def __replace_meas_counter(self, current_sil_file, current_file, sync_signal_name):
        r"""
        replace uiMeasurementCounter in current file with the AbsoluteTimestamp (uiTimestamp) used in labelling
        via Image Frame Counter (FrameID) provided in current_sil_file:

         1. get the FrameID for the MeasurementCounter of the frame
         2. search FrameID in \*_tstp.bsig
         3. add uiTimeStamp of \*_tstp.bsig to new index array

        push index array as signal 'AbsoluteTimeStamp' on data bus

        :param current_sil_file: path & filename of \*_tstp.bsig with uiTimeStamp and signals to synchronise it
        :type current_sil_file: string
        :param current_file: path and filename of \*.bsig file with all simulation output
        :type current_file:  string
        :param sync_signal_name: name of signal in sim output to synchronise to time stamp
        :type sync_signal_name:  string
        """
        with SignalReader(current_file) as reader:
            sync_ts = reader[sync_signal_name].tolist()

        with SignalReader(current_sil_file) as reader:
            # use pure signal names for Frame conversion as decided by Test Managers in Jun.14
            abs_ts = reader[SIL_FC_ABSOLUTE_TS].tolist()
            img_ts = reader[SIL_FRAME_CNR].tolist()

        offs = 0
        sil_ts = []
        for i in range(len(sync_ts)):
            for k in range(50):
                idx = i + offs - k
                if 0 <= idx < len(img_ts):
                    if img_ts[idx] != 0 and (img_ts[idx]) == (sync_ts[i]):
                        sil_ts.append(abs_ts[idx])
                        offs -= k
                        break
                idx = i + offs + k
                if k != 0 and 0 <= idx < len(img_ts):
                    if img_ts[idx] != 0 and (img_ts[idx]) == (sync_ts[i]):
                        sil_ts.append(abs_ts[idx])
                        offs += k
                        break
            else:  # not found during k-loop:
                sil_ts.append(0L)

        self._data_manager.set_data_port(SIL_SYNC_TS, sil_ts, self._bus_name)
        return sig_gd.RET_VAL_OK

    def __replace_timestamps(self, file_name, sync_signal_name,  # pylint: disable=R0912,R0914,R0915
                             timestamp_signal_name, new_signal_name=None):
        """
        used for HIL simulation results, for SIL the new method `replace_meas_counter` should be used

        - replace given signal name on data port directly with same signal values from given file
        - used here to adapt the time stamp from HIL simulation to the original one used in label db
        - overwrites the data port 'timestamp_signal_name' directly with new list

        the embedded frame time stamp should be used as sync signal name to synchronise the different files,
        error is raised if a difference in embedded time stamps is found or if number of both doesn't match

        :param file_name: name of !! bsig/bin  !! file where original time stamp is stored
        :param sync_signal_name: name of signal available in both (ori and new) files to synchronise the signals
        :param timestamp_signal_name: time stamp signal name as used in the HIL run
        :param new_signal_name: new name for time stamp signal to allow HIL output with different names than SIL,
                                default is same as timestamp_signal_name
        :returns: success or error
        """
        # Open the signal file and read the original signals (usually from SIL)
        with SignalReader(file_name) as reader:
            ori_timestamp = reader[timestamp_signal_name].tolist()
            ori_sync = reader[sync_signal_name].tolist()

        # Get the synchronisation signal from the newer export (usually HIL)
        new_sync = self._data_manager.get_data_port(sync_signal_name, self._bus_name)

        # --------------------------
        # Cut out the leading and ending timestamps from the new signals
        # --------------------------
        aouterdels = []

        # find the leading indexes to del
        i = 0  # index for ori
        j = 0  # index for new
        while i < len(ori_sync) and j < len(new_sync) and ori_sync[i] != new_sync[j]:
            if ori_sync[i] < new_sync[j]:
                i += 1
            else:
                aouterdels.append(j)
                j += 1

        jmin = j

        # find the ending indexes to del
        i = len(ori_sync) - 1  # index for ori
        j = len(new_sync) - 1  # index for new
        while i >= 0 and j >= 0 and ori_sync[i] != new_sync[j]:
            if ori_sync[i] > new_sync[j]:
                i -= 1
            else:
                aouterdels.append(j)
                j -= 1

        jmax = j

        if len(aouterdels) >= len(new_sync):
            self._logger.error("time stamp conversion failed because "
                               "there is no matching between the synchronisation signals")
            return sig_gd.RET_VAL_ERROR

        # -------------------
        # find the new timestamps and store the indexes without corresponding timestamp
        # -------------------
        ainnerdels = []
        anewtimestamps = [0] * len(new_sync)

        # set i to the first common value
        i = ori_sync.index(new_sync[jmin])

        # for each valid value of j (part of the new inner sync array)
        for j in xrange(jmin, jmax + 1):
            # find the next value of i fitting to the one of j...
            while i < len(ori_sync) and ori_sync[i] < new_sync[j]:
                i += 1

            # ... maybe we found a good one => we can store the timestamp and look for the next one
            if ori_sync[i] == new_sync[j]:
                anewtimestamps[j] = ori_timestamp[i]
                i += 1  # be sure that we don't use the same original timestamp twice
            # ... but maybe there is no original value at all => we may have to delete the j index
            else:
                ainnerdels.append(j)

        # --------------------
        # adapt the new timestamps to the data in the Del arrays
        # --------------------
        # TODO: implement the interpolation as facultative using a flag
        if True:
            # ------ interpolation ---------
            # only delete the outer del values...
            aalldels = aouterdels

            # and interpolate the inner ones
            i = 0  # index through the innerDels
            while i < len(ainnerdels):
                # find the first and the last index of the newTS array to interpolate
                first = last = ainnerdels[i]
                i += 1
                while i < len(ainnerdels) and ainnerdels[i] == last + 1:
                    last += 1
                    i += 1

                # ok, now we have the first and last index (can be equal)
                # next, calculate the interpolation step (use floats and only get to ints at the end)
                step = (anewtimestamps[last + 1] - anewtimestamps[first - 1]) / float(last - first + 2)
                for j in range(last - first + 1):
                    anewtimestamps[first + j] = long(round(anewtimestamps[first - 1] + step * (j + 1)))

        else:
            # ------ simple deletion ------
            aalldels = aouterdels + ainnerdels

        anewtimestamps = delete(narray(anewtimestamps), aalldels).tolist()

        # ------------------------
        # add the newly computed signal to the global data for comparison
        # ------------------------
        if new_signal_name is not None:
            signal_name = new_signal_name
        else:
            signal_name = timestamp_signal_name

        # ------------------------
        # go through the loaded signals and delete the parts which are unnecessary
        # ------------------------
        for addit_port_and_signal_name in self.__addit_port_and_signal_names:
            additionalsignal = self._data_manager.get_data_port(addit_port_and_signal_name[PORT_NAME], self._bus_name)
            additionalsignal = delete(narray(additionalsignal), aalldels).tolist()
            self._data_manager.set_data_port(addit_port_and_signal_name[PORT_NAME], additionalsignal, self._bus_name)

        self._data_manager.set_data_port(signal_name, anewtimestamps, self._bus_name)
#        self._data_manager.set_data_port(INDEXES_TO_DELETE, aalldels, self._bus_name)

        return sig_gd.RET_VAL_OK

    @staticmethod
    def __compare_lists(ori, new):
        """
        two list of values (e.g. time stamps) are compared, this method finds

         - dups: duplicate entries in new list
         - adds: entries only in new list
         - drops: entries not in same order as in ori or missing in new list compared to ori

        the list in ori does not have to been sorted

        used to compare embedded time stamps of original and HIL output simulation files

        :param ori: list of original values to compare to
        :param new: list of values to compare to ori
        :returns: tuple with lists of duplicated, added and dropped values

        example:

        ::

                               |drop      |drop   |drop
            ori = [  2, 4, 6,  8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30 ]
            new = [  2, 4, 6, 10, 12, 16, 14, 18, 20, 18, 22, 24, 25, 26, 28 ]
                                                      ^dup        ^add

        results in

        ::

            dups = [ 18 ]
            adds = [ 25 ]
            drops = [ 10, 14, 18 ]
        """
        # get duplicates in new
        seen = set()
        seen_add = seen.add
        # adds all elements it doesn't know yet to seen and all other to dups
        dups = set(x for x in new if x in seen or seen_add(x))
        # all elements in new but not in ori:
        adds = set(new).difference(ori)
        igns = set().union(dups, adds)

        drops = []
        oidx = 0
        for nidx in range(len(new)):
            if new[nidx] in igns:
                # duplicated or additional frame in new, skip immediately
                continue

            while ori[oidx] != new[nidx]:
                if new[nidx] in drops:
                    # already found, stay on current ori element but step to next new
                    oidx -= 1
                    break
                # dropped frame, mark and check next
                drops.append(ori[oidx])
                oidx += 1
                if oidx >= len(ori):
                    oidx = len(ori) - 1
                    break
            oidx += 1

        return dups, adds, drops

    @staticmethod
    def GetListFromDictList(dict_list, tag):  # pylint: disable=C0103
        """ Get an individual list of an item from a list of dicts.

        :param dict_list: The dictionary.
        :param tag: The tag in the dictionary to extract as a list.
        :return: List of the tag given.
        :todo: There may be a better way to do this.
        """
        extracted_list = []
        for new_dict in dict_list:
            extracted_list.append(new_dict[tag])
        return extracted_list


"""
CHANGE LOG:
-----------
 $Log: signal_extractor.py  $
 Revision 1.7 2017/10/05 10:35:31CEST Hospes, Gerd-Joachim (uidv8815) 
 fix SignalExtractor fails if max(objects) == max(obj.channels)
 Revision 1.6 2016/11/29 12:04:46CET Hospes, Gerd-Joachim (uidv8815)
 update docu
 Revision 1.5 2016/09/30 19:02:28CEST Hospes, Gerd-Joachim (uidv8815)
 new port PermittedEmptySignals added
 Revision 1.4 2015/12/07 08:26:14CET Mertens, Sven (uidv7805)
 additional pep8 cleanup
 Revision 1.3 2015/05/08 10:32:32CEST Hospes, Gerd-Joachim (uidv8815)
 add sig_read to add_additional_object_signals() call
 --- Added comments ---  uidv8815 [May 8, 2015 10:32:32 AM CEST]
 Change Package : 336598:1 http://mks-psad:7002/im/viewissue?selection=336598
 Revision 1.2 2015/05/05 10:07:31CEST Hospes, Gerd-Joachim (uidv8815)
 fix tests for additional and constant signals
 Revision 1.1 2015/04/23 19:05:48CEST Hospes, Gerd-Joachim (uidv8815)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
 Revision 1.42 2015/04/10 13:50:45CEST Mertens, Sven (uidv7805)
 removing defined value
 --- Added comments ---  uidv7805 [Apr 10, 2015 1:50:45 PM CEST]
 Change Package : 318014:3 http://mks-psad:7002/im/viewissue?selection=318014
 Revision 1.41 2015/04/07 16:57:09CEST Mertens, Sven (uidv7805)
 using lists directly
 Revision 1.40 2015/03/27 10:39:34CET Mertens, Sven (uidv7805)
 naming some internal method names
 --- Added comments ---  uidv7805 [Mar 27, 2015 10:39:34 AM CET]
 Change Package : 317742:2 http://mks-psad:7002/im/viewissue?selection=317742
 Revision 1.39 2015/03/27 09:54:22CET Mertens, Sven (uidv7805)
 removing calls to deprecated methods
 --- Added comments ---  uidv7805 [Mar 27, 2015 9:54:23 AM CET]
 Change Package : 317742:2 http://mks-psad:7002/im/viewissue?selection=317742
 Revision 1.38 2015/03/18 18:03:45CET Hospes, Gerd-Joachim (uidv8815)
 use signalreader in signal_extractor
 --- Added comments ---  uidv8815 [Mar 18, 2015 6:03:45 PM CET]
 Change Package : 319181:1 http://mks-psad:7002/im/viewissue?selection=319181
 Revision 1.36.1.1 2015/02/10 19:39:52CET Hospes, Gerd-Joachim (uidv8815)
 update docu, fix epydoc errors
 --- Added comments ---  uidv8815 [Feb 10, 2015 7:39:53 PM CET]
 Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
 Revision 1.36 2014/11/20 16:54:40CET Zafar, Sohaib (uidu6396)
 add SignaExtractor usage example to epydoc
 --- Added comments ---  uidu6396 [Nov 20, 2014 4:54:41 PM CET]
 Change Package : 253431:1 http://mks-psad:7002/im/viewissue?selection=253431
 Revision 1.35 2014/10/22 11:41:57CEST Weinhold, Oliver (uidg4236)
 Timestamp replacement for HIL recordings refined.
 --- Added comments ---  uidg4236 [Oct 22, 2014 11:41:58 AM CEST]
 Change Package : 273919:1 http://mks-psad:7002/im/viewissue?selection=273919
 Revision 1.34 2014/10/20 10:41:08CEST Ellero, Stefano (uidw8660)
 All signals of a bsig file for one loop (LoadData - ProcessData - PostProcessData) are now deleted in method
 PostProcessData of SignalExtractor.
 --- Added comments ---  uidw8660 [Oct 20, 2014 10:41:09 AM CEST]
 Change Package : 273146:1 http://mks-psad:7002/im/viewissue?selection=273146
 Revision 1.33 2014/09/22 16:38:52CEST Hospes, Gerd-Joachim (uidv8815)
 file names as string for the data ports
 --- Added comments ---  uidv8815 [Sep 22, 2014 4:38:53 PM CEST]
 Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
 Revision 1.32 2014/08/21 17:55:52CEST Hospes, Gerd-Joachim (uidv8815)
 add clear_cache, pep8 and pylint fixes
 --- Added comments ---  uidv8815 [Aug 21, 2014 5:55:53 PM CEST]
 Change Package : 253116:3 http://mks-psad:7002/im/viewissue?selection=253116
 Revision 1.31 2014/08/21 16:18:56CEST Hospes, Gerd-Joachim (uidv8815)
 add AdditonalObjectList (_aol) as received from Miklos Sandor
 --- Added comments ---  uidv8815 [Aug 21, 2014 4:18:57 PM CEST]
 Change Package : 253116:3 http://mks-psad:7002/im/viewissue?selection=253116
 Revision 1.30 2014/08/19 10:14:38CEST Hospes, Gerd-Joachim (uidv8815)
 add basename usage in sil sync
 --- Added comments ---  uidv8815 [Aug 19, 2014 10:14:38 AM CEST]
 Change Package : 253112:3 http://mks-psad:7002/im/viewissue?selection=253112
 Revision 1.29 2014/07/25 12:00:35CEST Mertens, Sven (uidv7805)
 try and catch when not set from config
 --- Added comments ---  uidv7805 [Jul 25, 2014 12:00:36 PM CEST]
 Change Package : 251181:1 http://mks-psad:7002/im/viewissue?selection=251181
 Revision 1.28 2014/07/25 11:17:50CEST Mertens, Sven (uidv7805)
 taking over changes from Rustam to improve memory consumption
 --- Added comments ---  uidv7805 [Jul 25, 2014 11:17:51 AM CEST]
 Change Package : 251181:1 http://mks-psad:7002/im/viewissue?selection=251181
 Revision 1.27 2014/07/18 10:55:02CEST Hospes, Gerd-Joachim (uidv8815)
 fix _tstp filename merge error
 --- Added comments ---  uidv8815 [Jul 18, 2014 10:55:03 AM CEST]
 Change Package : 244453:1 http://mks-psad:7002/im/viewissue?selection=244453
 Revision 1.26 2014/07/18 09:56:28CEST Hospes, Gerd-Joachim (uidv8815)
 epydoc update for timestamp
 --- Added comments ---  uidv8815 [Jul 18, 2014 9:56:29 AM CEST]
 Change Package : 244453:1 http://mks-psad:7002/im/viewissue?selection=244453
 Revision 1.25 2014/07/08 13:39:30CEST Hospes, Gerd-Joachim (uidv8815)
 rename sil sync tstp file to <CurrentFile>_tstp.<SimFileExtension>
 --- Added comments ---  uidv8815 [Jul 8, 2014 1:39:30 PM CEST]
 Change Package : 245453:1 http://mks-psad:7002/im/viewissue?selection=245453
 Revision 1.23 2014/07/04 10:30:49CEST Baust, Philipp (uidg5548)
 Fix: Wrong length for object lifetimes
 Fix: Wrong obj separation, when using eObjMaintenanceState
 Feature: Objects as GenericObjectList
 --- Added comments ---  uidg5548 [Jul 4, 2014 10:30:49 AM CEST]
 Change Package : 235081:1 http://mks-psad:7002/im/viewissue?selection=235081
 Revision 1.22 2014/06/16 10:11:36CEST Hospes, Gerd-Joachim (uidv8815)
 new sil sync via frame id using uiMeasurementCounter signal
 --- Added comments ---  uidv8815 [Jun 16, 2014 10:11:36 AM CEST]
 Change Package : 241725:1 http://mks-psad:7002/im/viewissue?selection=241725
 Revision 1.21 2014/05/12 13:45:46CEST Hecker, Robert (heckerr)
 Fixed some pylint and pep8 Issues.
 --- Added comments ---  heckerr [May 12, 2014 1:45:47 PM CEST]
 Change Package : 233911:1 http://mks-psad:7002/im/viewissue?selection=233911
 Revision 1.20 2014/05/12 07:29:44CEST Baust, Philipp (uidg5548)
 Added handling for signal eObjMaintenanceState as object separator
 --- Added comments ---  uidg5548 [May 12, 2014 7:29:44 AM CEST]
 Change Package : 232638:1 http://mks-psad:7002/im/viewissue?selection=232638
 Revision 1.19 2014/03/26 14:26:11CET Hecker, Robert (heckerr)
 Adapted code to python 3.
 --- Added comments ---  heckerr [Mar 26, 2014 2:26:11 PM CET]
 Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
 Revision 1.18 2014/02/19 17:18:35CET Hecker, Robert (heckerr)
 Updated SIL-SIL-Sync.
 --- Added comments ---  heckerr [Feb 19, 2014 5:18:35 PM CET]
 Change Package : 220308:1 http://mks-psad:7002/im/viewissue?selection=220308
 Revision 1.17 2013/12/02 10:05:14CET Burdea, Florin (uidv7080)
 current_sil_tmstmp_file bugfix.
 --- Added comments ---  uidv7080 [Dec 2, 2013 10:05:14 AM CET]
 Change Package : 199573:3 http://mks-psad:7002/im/viewissue?selection=199573
 Revision 1.16 2013/11/22 10:29:14CET Burdea, Florin (uidv7080)
 Change of constant HIL_TMSTAMP_FILE_EXT from .'tstp' to 'tstp'.
 --- Added comments ---  uidv7080 [Nov 22, 2013 10:29:15 AM CET]
 Change Package : 199573:3 http://mks-psad:7002/im/viewissue?selection=199573
 Revision 1.15 2013/11/22 08:01:02CET Burdea, Florin (uidv7080)
 Sil sync and Hil bug fix for .tstp
 --- Added comments ---  uidv7080 [Nov 22, 2013 8:01:03 AM CET]
 Change Package : 199573:3 http://mks-psad:7002/im/viewissue?selection=199573
 Revision 1.13.1.1 2013/11/21 17:22:50CET Burdea, Florin (uidv7080)
 Sil-Sil synchronization added for the jointSimulation;

 Bug-fix for Hil-Sil '.tstp', the dot of the bsig extension was missing.
 --- Added comments ---  uidv7080 [Nov 21, 2013 5:22:51 PM CET]
 Change Package : 199573:3 http://mks-psad:7002/im/viewissue?selection=199573
 Revision 1.13 2013/09/10 16:10:38CEST Hospes, Gerd-Joachim (uidv8815)
 fix error in HIL settings, fix pep8/pylint errors, update docu
 --- Added comments ---  uidv8815 [Sep 10, 2013 4:10:38 PM CEST]
 Change Package : 190320:1 http://mks-psad:7002/im/viewissue?selection=190320
 Revision 1.12 2013/09/09 17:44:47CEST Hospes, Gerd-Joachim (uidv8815)
 fix indentation
 --- Added comments ---  uidv8815 [Sep 9, 2013 5:44:47 PM CEST]
 Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
 Revision 1.11 2013/09/09 17:33:10CEST Hospes, Gerd-Joachim (uidv8815)
 fix error in time stamp parameter checking
 --- Added comments ---  uidv8815 [Sep 9, 2013 5:33:10 PM CEST]
 Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
 Revision 1.10 2013/09/09 17:13:48CEST Hospes, Gerd-Joachim (uidv8815)
 use util/logger again
 --- Added comments ---  uidv8815 [Sep 9, 2013 5:13:49 PM CEST]
 Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
 Revision 1.9 2013/09/06 10:30:04CEST Mertens, Sven (uidv7805)
 finalizing unittest problems by using new logger functionality
 --- Added comments ---  uidv7805 [Sep 6, 2013 10:30:04 AM CEST]
 Change Package : 196367:2 http://mks-psad:7002/im/viewissue?selection=196367
 Revision 1.8 2013/09/06 09:48:57CEST Mertens, Sven (uidv7805)
 correcting mistake done when rename needed
 --- Added comments ---  uidv7805 [Sep 6, 2013 9:48:57 AM CEST]
 Change Package : 196367:2 http://mks-psad:7002/im/viewissue?selection=196367
 Revision 1.7 2013/09/06 09:28:56CEST Mertens, Sven (uidv7805)
 changing log handler
 --- Added comments ---  uidv7805 [Sep 6, 2013 9:28:56 AM CEST]
 Change Package : 196367:2 http://mks-psad:7002/im/viewissue?selection=196367
 Revision 1.6 2013/08/15 17:24:54CEST Hospes, Gerd-Joachim (uidv8815)
 HIL timestamp conversion added
 --- Added comments ---  uidv8815 [Aug 15, 2013 5:24:54 PM CEST]
 Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
 Revision 1.5 2013/07/30 10:07:03CEST Raedler, Guenther (uidt9430)
 - fixed object extraction error for objects with  lifetime 1
 --- Added comments ---  uidt9430 [Jul 30, 2013 10:07:03 AM CEST]
 Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
 Revision 1.4 2013/06/13 11:24:36CEST Mertens, Sven (uidv7805)
 btw: disabling some pylint errors
 --- Added comments ---  uidv7805 [Jun 13, 2013 11:24:37 AM CEST]
 Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
 Revision 1.3 2013/06/13 11:13:56CEST Mertens, Sven (uidv7805)
 when deleting an variable it cannot be accessed a second time!
 Revision 1.2 2013/05/22 10:37:05CEST Mertens, Sven (uidv7805)
 alignment of imports, pylint error reduction
 --- Added comments ---  uidv7805 [May 22, 2013 10:37:05 AM CEST]
 Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
 Revision 1.1 2013/05/15 18:13:18CEST Hospes, Gerd-Joachim (uidv8815)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
     stk/valf/project.pj
 Revision 2.0 2013/02/20 08:25:23CET Raedler, Guenther (uidt9430)
 - support STK2.0 with packages
 --- Added comments ---  uidt9430 [Feb 20, 2013 8:25:23 AM CET]
 Change Package : 163448:3 http://mks-psad:7002/im/viewissue?selection=163448
 Revision 1.12 2012/07/24 10:13:57CEST Hanel, Nele (haneln)
 ensure, that alle objects, that were selected on any of the 6
 OOI-positions once, are extracted from the bin-file
 --- Added comments ---  haneln [Jul 24, 2012 10:14:02 AM CEST]
 Change Package : 103188:10 http://mks-psad:7002/im/viewissue?selection=103188
 Revision 1.11 2012/06/29 10:56:30CEST Spruck, Jochen (spruckj)
 Add IBEO objects reading
 --- Added comments ---  spruckj [Jun 29, 2012 10:56:30 AM CEST]
 Change Package : 98074:5 http://mks-psad:7002/im/viewissue?selection=98074
 Revision 1.10 2012/03/19 15:20:20CET Hielscher, Patrick (uidt6110)
 Removed "-1" cycle which was in the OOI object list every time the object changes
 --- Added comments ---  uidt6110 [Mar 19, 2012 3:20:21 PM CET]
 Change Package : 94393:2 http://mks-psad:7002/im/viewissue?selection=94393
 Revision 1.9 2012/02/08 12:41:12CET Raedler-EXT, Guenther (uidt9430)
 - allow signals not being in the binary file
 --- Added comments ---  uidt9430 [Feb 8, 2012 12:41:13 PM CET]
 Change Package : 93032:2 http://mks-psad:7002/im/viewissue?selection=93032
 Revision 1.8 2011/10/25 09:44:41CEST Castell Christoph (uidt6394) (uidt6394)
 Fixed object_list bug found by Nele.
 --- Added comments ---  uidt6394 [Oct 25, 2011 9:44:41 AM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.7 2011/10/24 19:59:17CEST Castell Christoph (uidt6394) (uidt6394)
 Fixed error with the generation of the OOI list.
 --- Added comments ---  uidt6394 [Oct 24, 2011 7:59:18 PM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.6 2011/10/24 15:38:50CEST Castell Christoph (uidt6394) (uidt6394)
 Changed garbage collector error to info.
 --- Added comments ---  uidt6394 [Oct 24, 2011 3:38:50 PM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.5 2011/10/18 15:54:17CEST Castell Christoph (uidt6394) (uidt6394)
 First new version. Testing and some efficiency updates required.
 --- Added comments ---  uidt6394 [Oct 18, 2011 3:54:17 PM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.4 2011/10/18 08:36:41CEST Castell Christoph (uidt6394) (uidt6394)
 New intermediate version.
 --- Added comments ---  uidt6394 [Oct 18, 2011 8:36:41 AM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.3 2011/08/22 14:48:08CEST Castell Christoph (uidt6394) (uidt6394)
 Updated version.
 --- Added comments ---  uidt6394 [Aug 22, 2011 2:48:08 PM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.2 2011/08/03 14:00:06CEST Castell Christoph (uidt6394) (uidt6394)
 Changed name to ValidationDataExtractor.
 --- Added comments ---  uidt6394 [Aug 3, 2011 2:00:06 PM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.1 2011/08/03 13:56:20CEST Castell Christoph (uidt6394) (uidt6394)
 Initial revision
 Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/05_Testing/05_Test_Environment/algo/
                          ars301_req_test/valf_tests/vpc/project.pj
 Revision 1.14 2011/07/21 16:02:45CEST Castell Christoph (uidt6394) (uidt6394)
 Removed unused code.
 --- Added comments ---  uidt6394 [Jul 21, 2011 4:02:46 PM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.13 2011/07/21 11:33:25CEST Castell Christoph (uidt6394) (uidt6394)
 Formatting updates to remove warings.
 Revision 1.12 2011/07/21 11:20:53CEST Castell Christoph (uidt6394) (uidt6394)
 Merge of 1.9.1.5 back into mainline.
 Revision 1.9.1.5 2011/07/21 08:27:05CEST Castell Christoph (uidt6394) (uidt6394)
 Added PreTerminate() function.
 --- Added comments ---  uidt6394 [Jul 21, 2011 8:27:06 AM CEST]
 Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
 Revision 1.9.1.4 2011/01/25 12:28:18CET Ovidiu Raicu (RaicuO)
 Modified data extractor to work with bin file sections.
 Revision 1.7 or higher of stk_bsig.py must be used.
 --- Added comments ---  RaicuO [Jan 25, 2011 12:28:19 PM CET]
 Change Package : 37852:2 http://mks-psad:7002/im/viewissue?selection=37852
 Revision 1.9.1.3 2010/12/14 10:11:08CET Gicu Benchea (bencheag)
 Add all the relevant objects to the object list
 Increase the minimum cycle time for the processed obejcts to 45
 (about 3 seconds)
 --- Added comments ---  bencheag [Dec 14, 2010 10:11:08 AM CET]
 Change Package : 50877:1 http://mks-psad:7002/im/viewissue?selection=50877
 Revision 1.9.1.2 2010/11/17 13:00:49CET Gicu Benchea (bencheag)
 Fix the relevant flag issue at the beginig of the file
 --- Added comments ---  bencheag [Nov 17, 2010 1:00:50 PM CET]
 Change Package : 50877:1 http://mks-psad:7002/im/viewissue?selection=50877
 Revision 1.9.1.1 2010/11/16 09:41:34CET Gicu Benchea (bencheag)
 Update the default object ID with -1
 --- Added comments ---  bencheag [Nov 16, 2010 9:41:34 AM CET]
 Change Package : 50877:1 http://mks-psad:7002/im/viewissue?selection=50877
 Revision 1.9 2010/10/04 06:54:35CEST Sorin Mogos (mogoss)
 * removed component_name from RegisterDataPort
 --- Added comments ---  mogoss [Oct 4, 2010 6:54:35 AM CEST]
 Change Package : 51595:1 http://mks-psad:7002/im/viewissue?selection=51595
 Revision 1.8 2010/10/03 11:39:54CEST Sorin Mogos (mogoss)
 * removed component name from SetDataPort
 --- Added comments ---  mogoss [Oct 3, 2010 11:39:54 AM CEST]
 Change Package : 51595:1 http://mks-psad:7002/im/viewissue?selection=51595
 Revision 1.7 2010/08/25 13:11:43CEST Sorin Mogos (mogoss)
 * updated for ars301 configuration
 --- Added comments ---  mogoss [Aug 25, 2010 1:11:43 PM CEST]
 Change Package : 39236:1 http://mks-psad:7002/im/viewissue?selection=39236
 Revision 1.6 2010/07/28 09:12:35CEST Gicu Benchea (bencheag)
 Use commun structure for Device and simulator object structure
 --- Added comments ---  bencheag [Jul 28, 2010 9:12:36 AM CEST]
 Change Package : 41177:1 http://mks-psad:7002/im/viewissue?selection=41177
 Revision 1.5 2010/07/26 14:32:15CEST Gicu Benchea (bencheag)
 Ignore the first cycles from the OOI list which are by default 0
 Object extractor - avoid to split the object when the counter is repeated
 --- Added comments ---  bencheag [Jul 26, 2010 2:32:16 PM CEST]
 Change Package : 41177:1 http://mks-psad:7002/im/viewissue?selection=41177
 Revision 1.4 2010/07/23 16:02:37CEST Gicu Benchea (bencheag)
 Bug fix in the OOI Relevant object extractor - 0 ID is a valid one
 --- Added comments ---  bencheag [Jul 23, 2010 4:02:37 PM CEST]
 Change Package : 41177:1 http://mks-psad:7002/im/viewissue?selection=41177
 Revision 1.3 2010/06/28 13:35:32CEST smogos
 * code clean-up
 * configuration changes
 --- Added comments ---  smogos [2010/06/28 11:35:32Z]
 Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
 Revision 1.2 2010/06/21 16:24:44EEST Sorin Mogos (smogos)
 * changed according to new configuration format
 --- Added comments ---  smogos [2010/06/21 13:24:45Z]
 Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
 Revision 1.17 2010/04/30 12:22:16EEST Gicu Benchea (gbenchea)
 Change the minimum object length from 2 to 10 cycles
 --- Added comments ---  gbenchea [2010/04/30 09:22:17Z]
 Change Package : 41177:1 http://LISS014:6001/im/viewissue?selection=41177
 Revision 1.16 2010/04/29 14:56:09EEST Gicu Benchea (gbenchea)
 Run time optimisation - remove the SafeListAccess function
 --- Added comments ---  gbenchea [2010/04/29 11:56:10Z]
 Change Package : 41177:1 http://LISS014:6001/im/viewissue?selection=41177
 Revision 1.15 2010/04/23 15:21:54EEST Gicu Benchea (gbenchea)
 Added by default the absoulte distance to the path
 --- Added comments ---  gbenchea [2010/04/23 12:21:54Z]
 Change Package : 41177:1 http://LISS014:6001/im/viewissue?selection=41177
 Revision 1.14 2010/04/19 15:52:29EEST Gicu Benchea (gbenchea)
 Bug fix related to the object index
 --- Added comments ---  gbenchea [2010/04/19 12:52:29Z]
 Change Package : 41177:1 http://LISS014:6001/im/viewissue?selection=41177
 Revision 1.13 2010/04/19 13:49:24EEST Gicu Benchea (gbenchea)
 Added start and stop index to the OOI object structure
 Added a reference pointer to the object dictionary
 Bug fix - Set data of the OOI object list
 --- Added comments ---  gbenchea [2010/04/19 10:49:24Z]
 Change Package : 41177:1 http://LISS014:6001/im/viewissue?selection=41177
 Revision 1.12 2010/03/19 11:51:49EET Sorin Mogos (smogos)
 * code customisation and bug-fixes
 --- Added comments ---  smogos [2010/03/19 09:51:49Z]
 Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
 Revision 1.11 2010/03/05 13:45:22EET Gicu Benchea (gbenchea)
 Add bus parameter to the constructor
 Remove not needed attributes from object and event structures
 Add the logger
 --- Added comments ---  gbenchea [2010/03/05 11:45:22Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.10 2010/03/04 09:08:01EET Gicu Benchea (gbenchea)
 Add the bus conection
 --- Added comments ---  gbenchea [2010/03/04 07:08:02Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.9 2010/02/19 11:28:51EET Ovidiu Raicu (oraicu)
 Added logger support and posibility to use ABAObject.
 --- Added comments ---  oraicu [2010/02/19 09:28:51Z]
 Change Package : 37852:1 http://LISS014:6001/im/viewissue?selection=37852
 Revision 1.8 2010/01/27 12:34:31CET Ovidiu Raicu (oraicu)
 Modified data_extractor to work with binary files.
 --- Added comments ---  oraicu [2010/01/27 11:34:31Z]
 Change Package : 34637:1 http://LISS014:6001/im/viewissue?selection=34637
 Revision 1.7 2010/01/13 14:13:52CET Gicu Benchea (gbenchea)
 Changes to work with Simulated object lists
 --- Added comments ---  gbenchea [2010/01/13 13:13:52Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.6 2009/11/23 14:07:30EET Gicu Benchea (gbenchea)
 Method how to associtate the relevant flag to the objects has been changed
 --- Added comments ---  gbenchea [2009/11/23 12:07:31Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.5 2009/11/23 10:31:58EET Gicu Benchea (gbenchea)
 Bug fix - Index overflow
 --- Added comments ---  gbenchea [2009/11/23 08:31:59Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.4 2009/11/18 08:40:53EET Gicu Benchea (gbenchea)
 Add the object list from the MTS Device
 --- Added comments ---  gbenchea [2009/11/18 06:40:53Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.3 2009/11/16 17:33:21EET Gicu Benchea (gbenchea)
 * Adaption for processing the Device objects
 * Improve drop ins detection
 * Add events plot functionality
 --- Added comments ---  gbenchea [2009/11/16 15:33:21Z]
 Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
 Revision 1.2 2009/11/09 11:22:14EET Sorin Mogos (smogos)
 * added acc statistic collector drop-in detection rule
 --- Added comments ---  smogos [2009/11/09 09:22:14Z]
 Change Package : 32501:1 http://LISS014:6001/im/viewissue?selection=32501
 Revision 1.1 2009/10/30 16:24:55EET dkubera
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
 05_Algorithm/ACC_AdaptiveCruiseControl/05_Testing/05_Test_Environment/acc/
 30_BBT_BlackBoxTest/20_RequirementTest/ACC_Performance/01_Source_Code/
 project.pj
"""
