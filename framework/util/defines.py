"""
crt.ecu_sil.defaults
--------------------

Constants for ECU-SIL Test
"""
import os
from datetime import datetime as actual_ts

__author__ = "Leidenberger Ralf"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 21:33:23CET $"


_dir = os.path.split(__file__)[0]
#print("_dir", _dir)
PLUGINS_DIR = os.path.abspath(os.path.join(_dir, "..", "..", "test_cases"))
TEST_DATA_OUT = os.path.abspath(os.path.join(_dir, "..", "..", "..", "..", "2_Output", "_data", "output",
                                             str(actual_ts.now().strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3])))  # deleted , ".."  for suiting the HPC work

TEST_DATA_OUT_hpc = os.path.abspath(os.path.join(_dir, "..", "..", "..", "..", "2_Output", "_data", "output",
                                             str(actual_ts.now().strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3])))
#print("TEST_DATA_OUT dir", TEST_DATA_OUT)

BUS_ECU_207 = "Bus#ECU207"
BUS_SIL_207 = "Bus#SIL207"

BUS_ECU_208 = "Bus#ECU208"
BUS_SIL_208 = "Bus#SIL208"

ECU_20_DIR = ""
SIL_20_DIR = ""
ECU_60_DIR = ""
SIL_60_DIR = ""

# Error codes.
RET_VAL_OK = 0
RET_VAL_ERROR = -1

# Cycle times.
CYCLE_TIME_20_S = 0.020
CYCLE_TIME_S = 0.1
CYCLE_TIME_MS = 100
CYCLE_TIME_SHORT_MS = 56.0
CYCLE_TIME_LONG_MS = 76.0

# Unit conversions
MPS2KPH = 3.6
KPH2MPS = 1.0 / 3.6

# Other defines
THOUSAND = 1000.0
MILLION = 1000000.0
BILLION = 1000000000.0

# Units
UNIT_MM = "mm"
UNIT_M = "m"
UNIT_KM = "km"
UNIT_US = "us"
UNIT_MS = "ms"
UNIT_S = "s"
UNIT_H = "h"
UNIT_MPS = "m/s"
UNIT_KMPH = "km/h"
UNIT_DEG = "deg"
UNIT_RAD = "rad"
UNIT_MPS2 = "m/s^2"
UNIT_DEGPS = "deg/s"
UNIT_RADPS = "rad/s"
UNIT_CURVE = "1/m"
UNIT_NONE = "none"

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
#
# Database modules
DBACC = "dbacc"
DBCAT = "dbcat"
DBOBJ = "dbobj"
DBENV = "dbenv"
DBFCT = "dbfct"
DBGBL = "dbgbl"
DBVAL = "dbval"
DBLBL = "dblbl"
DBPAR = "dbpar"
DBCAM = "dbcam"
DBCL = "dbcl"
DBSIM = "dbsim"
DBMET = "dbmet"

# Validation PORT definitions
GLOBAL_BUS_NAME = "global"
OBJECT_PORT_NAME = "Objects"
EVENTS_PORT_NAME = "Events"
ACC_EVENTS_PORT_NAME = "Acc_Events"
VDYDATA_PORT_NAME = "VDYData"
FCTDATA_PORT_NAME = "FCTData"
TIMESTAMP_PORT_NAME = "Timestamp"
CURRENT_FILE_PORT_NAME = "CurrentFile"
CURRENT_SIMFILE_PORT_NAME = "CurrentSimFile"
CURRENT_SECTIONS_PORT_NAME = "CurrentSections"
CURRENT_MEASID_PORT_NAME = "CurrentMeasId"
REMOVED_FILES_PORT_NAME = "RemovedFiles"
OOI_OBJECT_PORT_NAME = "OOIObjects"
IBEO_OBJECT_PORT_NAME = "IBEOObjects"
SOD_OBJECT_PORT_NAME = "SODObjects"
CYCLE_TIME_PORT_NAME = "SensorCycleTime"
CYCLE_COUNTER_PORT_NAME = "CycleCounter"
SUMMARY_DATA_PORT_NAME = "SummaryData"
FILE_DATA_PORT_NAME = "FileData"
FILE_COUNT_PORT_NAME = "FileCount"
IS_FINISHED_PORT_NAME = "IsFinished"
NUMBER_OF_OBJECTS_PORT_NAME = "OBJ_number_of_objects"
# DATA_BUS_NAMES stores a list of data bus names defined by simulation output pathes (e.g bus#1, bus#2, ...)
DATA_BUS_NAMES = "DataBusNames"
DATABASE_OBJECTS_PORT_NAME = "DataBaseObjects"
DATABASE_OBJECTS_CONN_PORT_NAME = "DatabaseObjectsConnections"
SIMSELECTION_PORT_NAME = "SimSelection"
SIMFILEEXT_PORT_NAME = "SimFileExt"
EXACTMATCH_PORT_NAME = "ExactMatch"
SIMCHECK_PORT_NAME = "SimCheck"
RECURSE_PORT_NAME = "Recurse"
OUTPUTDIRPATH_PORT_NAME = "OutputDirPath"
SIMFILEBASE_PORT_NAME = "SimFileBaseName"
SWVERSION_REG_PORT_NAME = "SWVersion_REG"
SWVERSION_PORT_NAME = "SWVersion"
DBCONNECTION_PORT_NAME = "DBConnection"
IS_DBCOLLECTION_PORT_NAME = "IsDbCollection"
SAVE_RESULT_IN_DB = "SaveResultInDB"
COLLECTION_NAME_PORT_NAME = "RecCatCollectionName"
COLLECTION_PORT_NAME = "CollectionName"
COLLECTION_LABEL_PORT_NAME = "CollectionLabel"
COLLECTIONID_PORT_NAME = "CollectionId"
PLAY_LIST_FILE_PORT_NAME = "BplFilePath"
CFG_FILE_PORT_NAME = "ConfigFileName"
CFG_FILE_VERSION_PORT_NAME = "ConfigFileVersions"
ERROR_TOLERANCE_PORT_NAME = "ErrorTolerance"
SIM_PATH_PORT_NAME = "SimOutputPath"
HPC_AUTO_SPLIT_PORT_NAME = 'HpcAutoSplit'
REPORT_FILE_PORT_NAME = "ReportFileName"
UCV_CONS_RESULTS_PORT_NAME = "UcvConstraintsResult"
UCV_CONS_SIGNAL_LIST_PORT_NAME = 'UcvConstraintsSignalList'
UCV_RESULTS_PORT_NAME = "UcvResults"

"""
$Log: defines.py  $
Revision 1.1 2020/03/25 21:33:23CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
