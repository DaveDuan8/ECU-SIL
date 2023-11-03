# -*- coding:utf-8 -*-
"""
harddisk_prepare
----------------

**Prepares a HardDisk, which comes back from the TestDrive to be ready
to copied onto the TestDataServer.**

**Features:**
    - Search Order File (*.csv)
    - Parse Order File
    - Create Target Folders
    - Move all *.rrecs which are not inside a Target Folder
      to a target Folder.
    - All *.rrecs, which are not fitting to a order will belisted to a output
      log file.

**UseCase:**
 Typically used when a Harddisk comes back from a test drive, filled with
 Recordings (*.rrecs) from MTS2.6

**Usage:**

harddiskprepare.py -r RootFolder

Parameters:
 -r RootFolder
    for the Folder architecture, where the order files (*.csv)
    are located, and where the preparation should be done. (e.g. "F:/")

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 15:50:02CET $
"""
# Import Python Modules --------------------------------------------------------
import csv
import os
import sys
import fnmatch
import shutil
from optparse import OptionParser
import datetime
import time
import traceback

# Defines ----------------------------------------------------------------------
WARN_MTS_RECS_NOT_FIT_TO_ORDER = 10
ERR_OK = 0
ERR_ERROR = -500
ERR_ROOT_FOLDER_MISSING = -501
ERR_ROOT_FOLDER_DOES_NOT_EXIST = -503


# Functions --------------------------------------------------------------------
def find(pattern, path):
    """
    find files in given folder and pattern.

    :param path:    Filepath to search for files
    :type path:     string
    :param pattern: wildcard pattern
    :type pattern:  string
    """
    result = []
    for root, _, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


# Classes ----------------------------------------------------------------------
class Order(object):
    """
    Order class, which works as contianer for all order relevant data
    beloning to one order file.

    :author: Robert Hecker
    :date:   2014.05.20
    """
    def __init__(self):
        self.order_file_path = ""
        self.order_data = {}
        self.target_folder = ""

    @staticmethod
    def _read_csv(file_path):
        """
        Read the csv based order file to get all necessary information.

        :param file_paths: path to *.csv file
        :type file_paths:  lis[string]
        :return: order
        :rtype: dictionary
        """
        order = {}
        f_obj = open(file_path, "rb")
        reader = csv.reader(f_obj)

        for line in reader:
            # decode what you receive:
            line = line[0]
            res = line.split(';')
            order[res[0].decode('iso8859-1')] = res[1].decode('iso8859-1')

        f_obj.close()

        return order

    def read_order_file(self, file_path):
        """
        :param file_path: path to the order file
        :type file_path:  string
        """
        self.order_file_path = os.path.abspath(file_path)
        self.order_data = self._read_csv(self.order_file_path)
        self.target_folder = ""

    def build_target_folder(self, file_path, root_folder, prefix='Endurance'):
        """
        Build the needed target path for all *.rrecs in the wanted style.
        This Functions does not create the folder on the root folder

        :param root_folder: root_path with order files in it.
        :type root_folder:  string
        :param prefix: Additional Prefix needed for folder creation
        :type prefix:  string
        """
        # Get the neede input to create folder names
        unix_start_ts = self.order_data[u'starting_date_time']
        unix_stop_ts = self.order_data[u'end_date_time']

        start_date = datetime.datetime.utcfromtimestamp(int(unix_start_ts)).strftime('%Y-%m-%d_%H%M')
        end_date = datetime.datetime.utcfromtimestamp(int(unix_stop_ts)).strftime('%Y-%m-%d_%H%M')
        print("CSV-File:  " + os.path.split(file_path)[1])
        print("StartTime: " + start_date + " UnixStartTS: " + str(unix_start_ts))
        print("StopTime:  " + end_date + " UnixStopTS:  " + str(unix_stop_ts))
        print("====================================================================")

        # Convert Unix Timestamp to Readable date
        start_date = datetime.datetime.utcfromtimestamp(int(unix_start_ts)).\
            strftime('%Y-%m-%d')

        order_file_name = os.path.split(self.order_file_path)[1]
        order_file_name = os.path.splitext(order_file_name)[0]
        self.target_folder = os.path.join(root_folder,
                                          prefix,
                                          start_date,
                                          order_file_name)

    def fit(self, unix_ts):
        """
        Check if given unix timestamp fit to the order

        :param unix_ts: Unix based timestamp in seconds
        :type inix_tx: integer
        """
        start_ts = int(self.order_data[u'starting_date_time'])
        end_ts = int(self.order_data[u'end_date_time'])

        # Added some magic numbers.
        # Excel calculation does not fit to script
        # Excel calculation has also som - 3600 inside.
        return unix_ts >= (start_ts - 9000) and unix_ts <= (end_ts - 7200)


class HardDiskPrepare(object):
    """
    Class, which is able to read the Order File *.csv
    create the needed target folders for this Order, and
    move all *.rrecs to there.

    :author: Robert Hecker
    """
    def __init__(self):
        self._orders = []

    @staticmethod
    def _find_rrecs(root, exclude_dirs):
        """
        find all *.rrecs files which are inside the root directory,
        or a subdirectory.

        :param root: directory path where to start the search
        :type root:  string
        :param exclude_dirs: direcories to exclude from search
        :type exclude_dirs: list[string]

        :return: found *.rrec files
        :rtype: list[string]
        """
        found_rrecs = []
        for dirpath, _, filenames in os.walk(root):
            for filename in [f for f in filenames if f.endswith(".rrec")]:
                if dirpath not in exclude_dirs:
                    found_rrecs.append(os.path.join(dirpath, filename))

        return found_rrecs

    def _move_rrecs(self, rrecs):
        """
        move all *.rrecs from the root to the target path

        :return: list of not processed recs
        :rtype: list[string]
        """

        # Go through all available Recordings and try to select that one which
        # fits to the current order.

        not_processed_rrecs = []
        for rrec in rrecs:
            filename = os.path.split(rrec)[1]
            datetime_string = filename[0:13]
            dts = datetime.datetime.strptime(datetime_string, '%Y%m%d_%H%M')
            dts.replace(second=0, microsecond=0)
            unix_ts = int(time.mktime(dts.utctimetuple()))

            moved = False
            for order in self._orders:
                if order.fit(unix_ts):
                    # Move the File to the destination
                    dest = os.path.join(order.target_folder, filename)
                    shutil.move(rrec, dest)
                    moved = True
            if not moved:
                not_processed_rrecs.append(rrec)

        return not_processed_rrecs

    def _write_err_file(self, root_folder, rrecs):
        """
        Creates a *.err file with all files inside,
        which can not be assigend to a order.

        :param root_folder: Folder, where to write a *.log
        :type root_folder: string
        """
        filename = "HardDiskPrepare_" + time.strftime("%Y%m%d_%H%M%S") + ".log"

        log_file = open(os.path.join(root_folder, filename), 'w')
        log_file.write('Following listed file can not be assigned'
                       'to a order:\n')

        for item in rrecs:
            log_file.write(item + '\n')

        log_file.close()

    def prepare(self, root_folder, prefix='Endurance'):
        """
        Do the whole HardDiskPreparation based on the given root folder

        1.) Search Order File (*.csv)
        2.) Parse Order File
        3.) Create Target Folders
        4.) Move all *.rrecs from root to target Folder

        :param root_folder: Drive Letter with the correct root path e.g. "g:"
        :type root_folder:  string
        :param prefix: Additional Prefix needed for folder creation
        :type prefix:  string
        """
        root_folder = os.path.abspath(root_folder)
        # Search all available order files *.csv files
        file_paths = find('*.csv', root_folder)

        # Read Metadata out from all order files
        for file_path in file_paths:
            order = Order()
            order.read_order_file(file_path)
            order.build_target_folder(file_path, root_folder, prefix)
            self._orders.append(order)

        exclude_dirs = []
        for order in self._orders:
            exclude_dirs.append(order.target_folder)
            # Create the target folder path
            if os.path.isdir(order.target_folder) is False:
                os.makedirs(order.target_folder)

        # Search for all rrecs which are on the harddisk.
        rrecs = self._find_rrecs(root_folder, exclude_dirs)

        # Start processing and sort files depending on order
        rest = self._move_rrecs(rrecs)

        # Check if all files are processed or not
        if len(rest) > 0:
            # Write Error Log File with all files inside,
            # which can not be assigned
            self._write_err_file(root_folder, rest)
            return WARN_MTS_RECS_NOT_FIT_TO_ORDER
        else:
            return ERR_OK


# Functions --------------------------------------------------------------------
def main():
    """main function"""

    error = 0
    version = "HardDiskPreparationTool Version 1.0.0"

    parser = OptionParser(usage="%prog [Options]",
                          version=version)
    parser.add_option("-r",
                      "--Root",
                      dest="root",
                      default="",
                      help="Root path, used to perform the needed actions")

    opt = parser.parse_args()

    if opt[0].root == "":
        error = ERR_ROOT_FOLDER_MISSING

    if error is ERR_OK and os.path.isdir(opt[0].root) is False:
        error = ERR_ROOT_FOLDER_DOES_NOT_EXIST

    if error == ERR_OK:
        try:
            hdp = HardDiskPrepare()
            error = hdp.prepare(opt[0].root)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            error = ERR_ERROR

    if error != ERR_OK:
        print("\n\nharddisk_prepare error:" + str(error))

    return error


if __name__ == "__main__":

    sys.exit(main())


"""
CHANGE LOG:
-----------
$Log: harddisk_prepare.py  $
Revision 1.2 2015/12/07 15:50:02CET Mertens, Sven (uidv7805) 
removing pep8 errors
Revision 1.1 2015/04/23 19:03:47CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.6 2014/06/13 09:22:22CEST Hecker, Robert (heckerr)
Some more updates in epydoc.
--- Added comments ---  heckerr [Jun 13, 2014 9:22:23 AM CEST]
Change Package : 238264:1 http://mks-psad:7002/im/viewissue?selection=238264
Revision 1.5 2014/06/04 10:23:33CEST Hecker, Robert (heckerr)
Added more log output.
--- Added comments ---  heckerr [Jun 4, 2014 10:23:33 AM CEST]
Change Package : 240915:1 http://mks-psad:7002/im/viewissue?selection=240915
Revision 1.4 2014/05/21 18:49:15CEST Hecker, Robert (heckerr)
Fix in UTC Time conversion.
--- Added comments ---  heckerr [May 21, 2014 6:49:16 PM CEST]
Change Package : 227494:1 http://mks-psad:7002/im/viewissue?selection=227494
Revision 1.3 2014/05/21 18:44:54CEST Hecker, Robert (heckerr)
Added magic constants, to get it working.
--- Added comments ---  heckerr [May 21, 2014 6:44:54 PM CEST]
Change Package : 227494:1 http://mks-psad:7002/im/viewissue?selection=227494
Revision 1.2 2014/05/20 11:55:48CEST Hecker, Robert (heckerr)
updated harddiskprepare to new requirements.
--- Added comments ---  heckerr [May 20, 2014 11:55:48 AM CEST]
Change Package : 236930:1 http://mks-psad:7002/im/viewissue?selection=236930
Revision 1.1 2014/05/16 20:54:09CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/cmd/project.pj
"""
