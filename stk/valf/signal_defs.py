"""
validation_global_defs.py
-------------------------

Global definitions.

:org:           Continental AG
:author:        Christoph Castell

:version:       $Revision: 1.7 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/11/28 09:19:12CET $

"""

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

# BPL file tag and attribute definitions
BPL_TAG_BATCH_LIST = "BatchList"
BPL_TAG_BATCH_ENTRY = "BatchEntry"
BPL_TAG_SECTION_LIST = "SectionList"
BPL_TAG_SECTION = "Section"
BPL_ATTR_FILE_NAME = "fileName"
BPL_ATTR_START_TIME = "startTime"
BPL_ATTR_END_TIME = "endTime"

CAT_REC_GLOBAL_LABEL_ABSTS = -1

ACC_PLOT_DAT_FILE = "plot_dat_file"
ACC_VIDEO_SEQ_FILE = "video_seq_file"
ROAD_EVENT_IMAGE = "roadeventimage"

# def enum(**enums):
#    return type('Enum', (), enums)


class enum(object):
    def __init__(self, **enums):
        self.__dict__ = enums

    def __getattr__(self, name):
        try:
            if name != '__bases__' and name != '__mro__':
                return self.__dict__[name]
        except:
            raise Exception("Type '%s' is not registered" % name)

    def GetAttributeName(self, id):
        if id is not None:
            for item in self.__dict__:
                if self.__dict__[item] == id:
                    return item

            raise Exception("Type with id '%i' is not registered" % id)
        # else:
        #    raise StandardError("id is None")

EVENT_TYPE = enum(NONE=0,
                  APPROACH=1,
                  DROP_IN=2,
                  DROP_OUT=3,
                  CUT_IN=4,
                  CUT_OUT=5,
                  ROAD=6,
                  ROAD_ESTIMATION=7,
                  BLOCKAGE_RADAR_IN_UNLABLED=8,
                  BLOCKAGE_RADAR=9,
                  BLOCKAGE_LABEL_NOT_DETECTED=10,
                  TUNNEL_FP=11,
                  TUNNEL_FN=12,
                  XY_PLOT=13,
                  STATIONARY_OBSTACLE=14,
                  RSP_HW_MONITOR_EVENT=15,
                  RSP_INTERFERENCE_EVENT=16,
                  ALN_STATE_EVENT=17,
                  ACTIVE_STATE_EVENT=18,
                  RSP_INTERFERENCE_MITIGATION=19,
                  RSP_INTERFERENCE_SUPPRESSION=20,
                  ALN_MON_EVENT_ALIGNED=21,
                  ALN_MON_EVENT_MISALIGNED=22,
                  ALN_MON_EVENT_ADJUSTMENT_STAT=23,
                  TRUE_POSITIVE=24,
                  TRUE_NEGATIVE=25,
                  FALSE_POSITIVE=26,
                  FALSE_NEGATIVE=27,
                  TEST_EVENT=28,
                  CUTIN_TESTCASE=29,
                  APPROACH_TESTCASE=30,
                  APPROACH_STATIONARY=31,
                  CUTIN_OOI=32,
                  REGR_DIFFERENT_OBJECT=33,
                  REGR_DIFFERENT_OBJECT_COPY=34,
                  REGR_EARLY_SELECTION=35,
                  REGR_LATE_SELECTION=36,
                  REGR_EARLY_DESELECTION=37,
                  REGR_LATE_DESELECTION=38,
                  REGR_SELECTED_NEW=39,
                  REGR_SELECTED_OLD=40,
                  REGR_DESELECTED_OLD=41,
                  REGR_DESELECTED_NEW=42,
                  REGR_CMS_LEVEL=43,
                  EGO_LANE_CHANGE_PROB_POTENTIAL=44,
                  EGO_LANE_CHANGE_PROB_TESTCASE=45,
                  NUM_EVENT_TYPE=46,
                  STOPPING_CONDITION=47)

ASSESSMENT = enum(VALID='Valid',
                  INVALID='Invalid',
                  NOT_ASSESSED='Not assessed',
                  INVESTIGATE='Investigate',
                  NOT_ASSESSABLE='Not assessable',
                  RULE_NOT_DEFINED='Rule Not Defined',
                  MINUS_TWO='-2',
                  MINUS_ONE='-1',
                  NULL='0',
                  PLUS_ONE='+1',
                  PLUS_TWO='+2')

# OBJECT Definitions
OBJ_OBJECT_INDEX = "Index"
OBJ_GLOBAL_ID = "GlobalObjectId"
OBJ_OBJECT_ID = "ObjectId"
OBJ_DYNAMIC_PROPERTY = "ucDynamicProperty"
OBJ_START_TIME = "StartTime"
OBJ_START_INDEX = "Index"
OBJ_TIME_STAMPS = "Timestamp"
OBJ_RECTOBJECT_ID = "RectObjId"
OBJ_CLASS = "Classification"


OBJ_DISTX = 'DistX'
OBJ_DISTX_STD = 'DistX_Std'
OBJ_DISTY = 'DistY'
OBJ_DISTY_STD = 'DistY_Std'
OBJ_VELX = 'VrelX'
OBJ_VELX_STD = 'VrelX_Std'
OBJ_VELY = 'VrelY'
OBJ_VELY_STD = 'VrelY_Std'
OBJ_ACCELX = 'AccelX'
OBJ_ACCELX_STD = 'AccelX_Std'
OBJ_ACCELY = 'AccelY'
OBJ_ACCELY_STD = 'AccelY_Std'
OBJ_ORIENT = 'Orient'
OBJ_ORIENT_STD = 'Orient_Std'
OBJ_FLAG = 'Flags'
OBJ_LENGTH = 'Object_Length'
OBJ_WIDTH = 'Object_Width'

OBJECT_PROPERTY = enum(OBJECT_PROPERTY_MOVING=0,
                       OBJECT_PROPERTY_STATIONARY=1,
                       OBJECT_PROPERTY_ONCOMING=2,
                       OBJECT_PROPERTY_STOPPED=3,
                       OBJECT_PROPERTY_FREE=4,
                       OBJECT_PROPERTY_UNDEFINED=5)

OBJECT_PROPERTY_STOPPED = 3
OBJECT_PROPERTY_ONCOMING = 2  # Oncomming Object
OBJECT_PROPERTY_STATIONARY = 1  # Stationary Object
OBJECT_PROPERTY_MOVING = 0  # Moving Object

# not used anymore - define some dummy values
OBJECT_PROPERTY_UNDEFINED = 200
OBJECT_PROPERTY_FREE = 201

OBJ_TYPE_MAP = {OBJECT_PROPERTY_MOVING: 'OBJECT_PROPERTY_MOVING',
                OBJECT_PROPERTY_STATIONARY: 'OBJECT_PROPERTY_STATIONARY',
                OBJECT_PROPERTY_ONCOMING: 'OBJECT_PROPERTY_ONCOMING',
                OBJECT_PROPERTY_STOPPED: 'OBJECT_PROPERTY_STOPPED',
                OBJECT_PROPERTY_FREE: 'OBJECT_PROPERTY_FREE',
                OBJECT_PROPERTY_UNDEFINED: 'OBJECT_PROPERTY_UNDEFINED'}

OBJECT_CLASS = enum(POINT=0,
                    CAR=1,
                    TRUCK=2,
                    PEDESTRIAN=3,
                    MOTORCYCLE=4,
                    BICYCLE=5,
                    WIDE=6,
                    UNCLASSIFIED=7
                    )

CLASS_UNKNOWN = 0
CLASS_CAR = 1
CLASS_TRUCK = 2
CLASS_BIKE = 3
CLASS_PEDESTRIAN = 4

CLASS_ID_MAP = {CLASS_UNKNOWN: 'Unknown',
                CLASS_CAR: 'Car',
                CLASS_TRUCK: 'Truck',
                CLASS_BIKE: 'Bike',
                CLASS_PEDESTRIAN: 'Pedestrian'}


# Vehicle Dynamics Definitions
PORT_VDY_VEHICLE_SPEED = "VehicleSpeed"
PORT_VDY_VEHICLE_ACCEL = "VehicleAccelXObjSync"
PORT_VDY_VEHICLE_CURVE = "VehicleCurveObjSync"
PORT_VDY_VEHICLE_YAWRATE = "VehicleYawRateObjSync"


#  Error Monitor Signal States defined for VDY, RSP, ...
MON_SIG_STATE_UNKNOWN = 0
MON_SIG_STATE_INACTIVE = 2
MON_SIG_STATE_ACTIVE = 1

# define possible customers for switching between different customer specific functionalities
# (maybe even projects like BMW 350 / BMW 353, DAI 310 / DAI 315)
CUSTOMER_DAI = "Daimler"
CUSTOMER_BMW = "BMW"

LBLSTATE = enum(UNLABELED=0,
                AUTO=1,
                MANUAL=2,
                REVIEWED=3)

WORKFLOW = enum(MANUAL=0,
                AUTOMATIC=1,
                VERIFIED=2,
                REJECTED=3)

DB_LANE = enum(UNKNOWN_LANE=5,
               FARLEFT_LANE=4,
               LEFT_LANE=3,
               EGO_LANE=2,
               RIGHT_LANE=1,
               FARRIGHT_LANE=0)

# ------------ log -----------

"""
CHANGE LOG:
-----------
$Log: signal_defs.py  $
Revision 1.7 2016/11/28 09:19:12CET Hospes, Gerd-Joachim (uidv8815) 
add new states for acc
Revision 1.6 2016/09/20 18:24:51CEST Hospes, Gerd-Joachim (uidv8815)
add dbmet def
Revision 1.5 2016/07/11 12:03:09CEST Mertens, Sven (uidv7805)
CollectionLabel needs to be part of config
Revision 1.4 2016/06/21 13:53:59CEST Hospes, Gerd-Joachim (uidv8815)
add config file versions and tests for it
Revision 1.3 2015/06/16 17:31:59CEST Hospes, Gerd-Joachim (uidv8815)
added STOPPING_CONDITION from Jan (EBA)
- Added comments -  uidv8815 [Jun 16, 2015 5:31:59 PM CEST]
Change Package : 348145:1 http://mks-psad:7002/im/viewissue?selection=348145
Revision 1.2 2015/04/30 11:09:29CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:30 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:05:48CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.15 2015/04/27 14:34:17CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:34:17 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.14 2015/04/24 12:43:32CEST Mertens, Sven (uidv7805)
adding fct as well
--- Added comments ---  uidv7805 [Apr 24, 2015 12:43:33 PM CEST]
Change Package : 331116:2 http://mks-psad:7002/im/viewissue?selection=331116
Revision 1.13 2015/03/20 10:27:02CET Mertens, Sven (uidv7805)
adding DBConnection
--- Added comments ---  uidv7805 [Mar 20, 2015 10:27:03 AM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.12 2015/03/19 16:53:06CET Mertens, Sven (uidv7805)
adding missing defines
--- Added comments ---  uidv7805 [Mar 19, 2015 4:53:07 PM CET]
Change Package : 319697:1 http://mks-psad:7002/im/viewissue?selection=319697
Revision 1.11 2015/03/11 16:29:58CET Mertens, Sven (uidv7805)
adding port names for collection reader
--- Added comments ---  uidv7805 [Mar 11, 2015 4:29:58 PM CET]
Change Package : 314923:3 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.10 2015/02/10 19:39:47CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:49 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.9 2015/01/29 15:14:09CET Mertens, Sven (uidv7805)
COLLECTION_PORT_NAME supporting CollectionName
--- Added comments ---  uidv7805 [Jan 29, 2015 3:14:09 PM CET]
Change Package : 288765:1 http://mks-psad:7002/im/viewissue?selection=288765
Revision 1.8 2014/12/19 12:28:13CET Ahmed, Zaheer (uidu7634)
add event type in enum ego lane change probablity potential, ego lane change probablity  statistic
--- Added comments ---  uidu7634 [Dec 19, 2014 12:28:14 PM CET]
Change Package : 279151:2 http://mks-psad:7002/im/viewissue?selection=279151
Revision 1.7 2014/10/08 12:49:48CEST Wartenberg, Jan (uidw3910)
Bugfix
--- Added comments ---  uidw3910 [Oct 8, 2014 12:49:49 PM CEST]
Change Package : 269148:4 http://mks-psad:7002/im/viewissue?selection=269148
Revision 1.6 2014/09/25 16:39:07CEST Hospes, Gerd-Joachim (uidv8815)
add OBJ_WIDTH, OBJ_LENGTH, rem. dublicate OBJECT_ID
--- Added comments ---  uidv8815 [Sep 25, 2014 4:39:07 PM CEST]
Change Package : 264199:1 http://mks-psad:7002/im/viewissue?selection=264199
Revision 1.5 2014/03/26 14:26:10CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.4 2013/12/17 10:34:32CET Hospes, Gerd-Joachim (uidv8815)
add use case validation port names 'UCV_*'
--- Added comments ---  uidv8815 [Dec 17, 2013 10:34:33 AM CET]
Change Package : 208339:1 http://mks-psad:7002/im/viewissue?selection=208339
Revision 1.2 2013/09/19 10:43:29CEST Raedler, Guenther (uidt9430)
- defined new port names
--- Added comments ---  uidt9430 [Sep 19, 2013 10:43:30 AM CEST]
Change Package : 197855:1 http://mks-psad:7002/im/viewissue?selection=197855
Revision 1.1 2013/05/15 18:13:17CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
Revision 2.0 2013/02/20 08:35:45CET Raedler, Guenther (uidt9430)
- Support STK2.0 with packages
--- Added comments ---  uidt9430 [Feb 20, 2013 8:35:45 AM CET]
Change Package : 175124:1 http://mks-psad:7002/im/viewissue?selection=175124
Revision 1.44 2013/01/24 17:23:37CET Apel, Norman (apeln)
- set cycletime for ARS400 B0 Sample to 0.1s for Radar Main Cycle
--- Added comments ---  apeln [Jan 24, 2013 5:23:37 PM CET]
Change Package : 172127:7 http://mks-psad:7002/im/viewissue?selection=172127
Revision 1.43 2012/12/13 09:32:47CET Bratoi, Bogdan-Horia (uidu8192)
- adding ROAD_EVENT_IMAGE definition
--- Added comments ---  uidu8192 [Dec 13, 2012 9:32:50 AM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.42 2012/11/26 10:10:56CET Bratoi, Bogdan-Horia (uidu8192)
- adding 2 defs for plot and image files (used in ACC and Valgui)
--- Added comments ---  uidu8192 [Nov 26, 2012 10:10:56 AM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.41 2012/11/05 13:36:40CET Bratoi, Bogdan-Horia (uidu8192)
-added new event types
--- Added comments ---  uidu8192 [Nov 5, 2012 1:36:42 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.40 2012/10/18 16:46:17CEST Hammernik-EXT, Dmitri (uidu5219)
- added new eventtypes
- added/ changed values in OBJECT_CLASS
--- Added comments ---  uidu5219 [Oct 18, 2012 4:46:19 PM CEST]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.39 2012/10/10 11:17:21CEST Hammernik-EXT, Dmitri (uidu5219)
- added assessment definition
- bugfix in enum
--- Added comments ---  uidu5219 [Oct 10, 2012 11:17:21 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38 2012/08/24 09:05:46CEST Hammernik-EXT, Dmitri (uidu5219)
-added new event_types and object properties
--- Added comments ---  uidu5219 [Aug 24, 2012 9:05:47 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.37 2012/07/18 09:01:24CEST Hammernik-EXT, Dmitri (uidu5219)
- added new Portname
- bugfix in enum class
--- Added comments ---  uidu5219 [Jul 18, 2012 9:01:24 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.36 2012/07/16 16:44:14CEST Raedler Guenther (uidt9430) (uidt9430)
- added definition for parameter tables
--- Added comments ---  uidt9430 [Jul 16, 2012 4:44:14 PM CEST]
Change Package : 136608:1 http://mks-psad:7002/im/viewissue?selection=136608
Revision 1.35 2012/07/06 15:19:27CEST Spruck, Jochen (spruckj)
Move collection distance summary calculation to val
--- Added comments ---  spruckj [Jul 6, 2012 3:19:27 PM CEST]
Change Package : 98074:5 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.34 2012/07/02 13:41:38CEST Hammernik-EXT, Dmitri (uidu5219)
- removed OPERATIONS enum
- added LBLSTATE
- DB_LANE
- bugfix in the enum class
--- Added comments ---  uidu5219 [Jul 2, 2012 1:41:38 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.33 2012/06/05 14:46:04CEST Hammernik-EXT, Dmitri (uidu5219)
- bugfix in enum type defenition
--- Added comments ---  uidu5219 [Jun 5, 2012 2:46:04 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.32 2012/06/05 13:52:48CEST Hammernik-EXT, Dmitri (uidu5219)
- added new Portname: IBEO_OBJECT_PORT_NAME
- changed enum type defenition
- added some new Event types in EVENT_TYPE
- added ASSESSMENT
--- Added comments ---  uidu5219 [Jun 5, 2012 1:52:53 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.31 2012/05/15 10:40:21CEST Hammernik-EXT, Dmitri (uidu5219)
- added new enum -> operations
Revision 1.30 2012/04/24 15:12:11CEST Spruck, Jochen (spruckj)
Some changes regarding the observer recording statistics
--- Added comments ---  spruckj [Apr 24, 2012 3:12:11 PM CEST]
Change Package : 98074:3 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.29 2012/03/20 11:33:48CET Spruck, Jochen (spruckj)
Add recording driven distances for different types to the base report
--- Added comments ---  spruckj [Mar 20, 2012 11:33:48 AM CET]
Change Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.28 2012/03/15 10:52:25CET Hanel, Nele (haneln)
added defines for customer switches
--- Added comments ---  haneln [Mar 15, 2012 10:52:26 AM CET]
Change Package : 103188:3 http://mks-psad:7002/im/viewissue?selection=103188
Revision 1.27 2012/02/24 09:47:00CET Farcas-EXT, Florian Radu (uidu4753)
Added 2 new generic functions for report generation
(summary header, testcase header)
--- Added comments ---  uidu4753 [Feb 24, 2012 9:47:00 AM CET]
Change Package : 100297:1 http://mks-psad:7002/im/viewissue?selection=100297
Revision 1.26 2012/02/06 17:07:04CET Hammernik-EXT, Dmitri (uidu5219)
added additional Portnames
--- Added comments ---  uidu5219 [Feb 6, 2012 5:07:06 PM CET]
Change Package : 91989:2 http://mks-psad:7002/im/viewissue?selection=91989
Revision 1.25 2011/12/19 18:04:57CET Farcas-EXT, Florian Radu (uidu4753)
Added ALN_MON_EVENT
--- Added comments ---  uidu4753 [Dec 19, 2011 6:04:57 PM CET]
Change Package : 92166:1 http://mks-psad:7002/im/viewissue?selection=92166
Revision 1.24 2011/12/15 14:12:54CET Raedler-EXT, Guenther (uidt9430)
- added 20ms cycle time
- added states for error monitor signals
--- Added comments ---  uidt9430 [Dec 15, 2011 2:12:54 PM CET]
Change Package : 88150:1 http://mks-psad:7002/im/viewissue?selection=88150
Revision 1.23 2011/12/05 14:50:59CET Castell, Christoph (uidt6394)
Added
CYCLE_TIME_SHORT_MS = 56.0
CYCLE_TIME_LONG_MS  = 76.0
These cycle time limits are used by the Validation GUI to check how many
cycles of a file are bad.
--- Added comments ---  uidt6394 [Dec 5, 2011 2:50:59 PM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.22 2011/11/22 16:51:47CET Raedler Guenther (uidt9430) (uidt9430)
- global port name to store the data bus names used in validation_main
--- Added comments ---  uidt9430 [Nov 22, 2011 4:51:47 PM CET]
Change Package : 88150:1 http://mks-psad:7002/im/viewissue?selection=88150
Revision 1.21 2011/11/15 10:55:02CET Raedler Guenther (uidt9430) (uidt9430)
- added new event types
--- Added comments ---  uidt9430 [Nov 15, 2011 10:55:02 AM CET]
Change Package : 76661:1 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.20 2011/11/11 09:30:55CET Castell Christoph (uidt6394) (uidt6394)
Added VDY port names.

PORT_VDY_VEHICLE_SPEED      = "VehicleSpeed"
PORT_VDY_VEHICLE_ACCEL      = "VehicleAccelXObjSync"
PORT_VDY_VEHICLE_CURVE      = "VehicleCurveObjSync"
PORT_VDY_VEHICLE_YAWRATE    = "VehicleYawRateObjSync"
--- Added comments ---  uidt6394 [Nov 11, 2011 9:30:56 AM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.19 2011/11/11 09:08:24CET Castell Christoph (uidt6394) (uidt6394)
Increased accuracy of cycle time from 66 ms to 66.67 ms. The intention is
to replace this value
with the real cycle time taken from the timestamp array wherever possible.
--- Added comments ---  uidt6394 [Nov 11, 2011 9:08:24 AM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.18 2011/11/07 15:33:37CET Raedler Guenther (uidt9430) (uidt9430)
- added new obj signal names
--- Added comments ---  uidt9430 [Nov 7, 2011 3:33:37 PM CET]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.17 2011/11/04 14:08:03CET Raedler Guenther (uidt9430) (uidt9430)
- new event type
--- Added comments ---  uidt9430 [Nov 4, 2011 2:08:04 PM CET]
Change Package : 86868:1 http://mks-psad:7002/im/viewissue?selection=86868
Revision 1.16 2011/10/27 15:37:07CEST Raedler Guenther (uidt9430) (uidt9430)
- added new global object name definitions
--- Added comments ---  uidt9430 [Oct 27, 2011 3:37:07 PM CEST]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.15 2011/10/24 14:59:37CEST Castell Christoph (uidt6394) (uidt6394)
Changed "TPECUCycleCounter" tag name to "CycleCounter"
as tag name was misleading.
Replaced MAX_OBJECT_NR define with NUMBER_OF_OBJECTS_PORT_NAME.
The value is located in the config file.
--- Added comments ---  uidt6394 [Oct 24, 2011 2:59:38 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.14 2011/10/19 08:35:25CEST Raedler Guenther (uidt9430) (uidt9430)
- added new globals for class observer
- added new common port names
--- Added comments ---  uidt9430 [Oct 19, 2011 8:35:25 AM CEST]
Change Package : 62766:2 http://mks-psad:7002/im/viewissue?selection=62766
Revision 1.13 2011/10/14 11:51:52CEST Castell Christoph (uidt6394) (uidt6394)
Added FCTDATA_PORT_NAME.
--- Added comments ---  uidt6394 [Oct 14, 2011 11:51:53 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/10/07 07:45:12CEST Raedler Guenther (uidt9430) (uidt9430)
- extened validation event class
- added new class for stationary obstacles
- added global defines
--- Added comments ---  uidt9430 [Oct 7, 2011 7:45:12 AM CEST]
Change Package : 76661:3 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.11 2011/09/20 16:07:48CEST Castell Christoph (uidt6394) (uidt6394)
Added BPL file tag and attribute definitions.
--- Added comments ---  uidt6394 [Sep 20, 2011 4:07:49 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.10 2011/09/20 11:30:30CEST Raedler Guenther (uidt9430) (uidt9430)
- added event class code into drop in and drop out observers
- moved port names from acc_global_defs into validation global defs
--- Added comments ---  uidt9430 [Sep 20, 2011 11:30:30 AM CEST]
Change Package : 76661:2 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.9 2011/09/05 13:07:51CEST Castell Christoph (uidt6394) (uidt6394)
Added UNIT_NONE and UNIT_L_NONE.
--- Added comments ---  uidt6394 [Sep 5, 2011 1:07:51 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.8 2011/09/02 13:17:29CEST Spruck Jochen (spruckj) (spruckj)
Add unit definition for curve
--- Added comments ---  spruckj [Sep 2, 2011 1:17:29 PM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.7 2011/09/02 11:40:15CEST Castell Christoph (uidt6394) (uidt6394)
Added support for label database.
--- Added comments ---  uidt6394 [Sep 2, 2011 11:40:15 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.6 2011/08/25 13:51:56CEST Raedler Guenther (uidt9430) (uidt9430)
add event specific definition
add global enum type
--- Added comments ---  uidt9430 [Aug 25, 2011 1:51:56 PM CEST]
Change Package : 62766:1 http://mks-psad:7002/im/viewissue?selection=62766
Revision 1.5 2011/08/12 17:21:02CEST Castell Christoph (uidt6394) (uidt6394)
Units.
--- Added comments ---  uidt6394 [Aug 12, 2011 5:21:02 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.4 2011/08/12 16:47:47CEST Castell Christoph (uidt6394) (uidt6394)
Added unit defs.
Revision 1.3 2011/07/27 11:04:11CEST Castell Christoph (uidt6394) (uidt6394)
Added database modules.
--- Added comments ---  uidt6394 [Jul 27, 2011 11:04:11 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/07/20 14:34:37CEST Castell Christoph (uidt6394) (uidt6394)
First working version.
--- Added comments ---  uidt6394 [Jul 20, 2011 2:34:37 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.1 2011/07/20 12:21:45CEST Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/
05_Testing/05_Test_Environment/algo/ars301_req_test/valf_tests/vpc/project.pj
"""
