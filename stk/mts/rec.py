"""
stk/mts/rec
-----------

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.3 $
:date:          $Date: 2017/06/21 15:33:02CEST $
"""
# Import Python Modules --------------------------------------------------------
from sys import argv
from os import path, getcwd, makedirs, removedirs, listdir, unlink, remove, sep
from subprocess import Popen, PIPE
from shutil import copy
from re import search as research, findall
import six

# Import STK Modules -----------------------------------------------------------
try:
    from . __rec import pyrecreader as rec
except:
    rec = None
from .. util.logger import Logger
from .. util.helper import deprecation

# Defines ----------------------------------------------------------------------
DEFAULT_OUTPUT_DIR_PATH = getcwd()
DEFAULT_GFX_OUTPUT_SUBDIR = "gfx"
SEQ_FOLDER_NAME = "video"
SEQ_FILE_EXT = ".seq"
RECFILEEXTRACTOR_SKIP_MICROS = 500000


# Classes ----------------------------------------------------------------------
class RecFileReader(object):
    r"""
    Class to which offers functionality for open and reading the content of
    a rec file.

    **Class usage example:**

    .. python::

        # Import RecFileReader STK module
        from stk.mts import RecFileReader

        # Defines ----------------------------------------------------------------------
        REC_FILE = unicode(os.path.abspath(os.path.join(os.path.split(__file__)[0],
                                                        r"..\..\..\04_Test_Data\01_Input\mts\MFC31X_7samples.rec")))

        # Same code examples -----------------------------------------------------------

        def test_open():

            rec = RecFileReader()
            rec.open(REC_FILE)
            rec.close()

        def test_device_count():

            rec = RecFileReader()
            rec.open(REC_FILE)
            count = rec.device_count
            rec.close()

        def test_timestamps():

            rec = RecFileReader()
            rec.open(REC_FILE)
            start_ts = rec.start_timestamp
            stop_ts = rec.stop_timestamp
            curr_ts = rec.curr_timestamp
            rec.close()

            print curr_ts

        def test_read():

            rec = RecFileReader()
            rec.open(REC_FILE)

            for i in range(0, 10):
                print rec.read()
                print rec.curr_timestamp
                # rec.jump(0)

            rec.close()

            ...

    :author:        Robert Hecker
    :date:          13.07.2014
    """
    def __init__(self):
        if rec is None:
            raise NotImplementedError("recfilereader isn't currently support")
        self.__file_id = None

    def open(self, rec_file_path):
        """
        Opens a recording file with a given path.

        :param rec_file_path: absolute path to the recording file
        :type rec_file_path: unicode
        """
        self.__file_id = rec.open(rec_file_path)

    def close(self):
        """
        Closes an already opened rec file.

        **1. Example:**

        .. python::
            REC_FILE = unicode(r"C:\\path\\to\\myrecording.rec")
            rec = RecFileReader()
            rec.open(REC_FILE)
            rec.close()
        """
        rec.close(self.__file_id)

    @property
    def start_timestamp(self):
        """
        Provides the timestamp of the first package of the opened recording
        in microseconds.

        :return: returns the start timestamp of the opened recording
        :rtype: long
        """
        return rec.get_start_timestamp(self.__file_id)

    @property
    def stop_timestamp(self):
        """
        Provides the timestamp of last package of the opened recording
        in microseconds.

        :return: returns the stop timestamp of the opened recording
        :rtype: long
        """
        return rec.get_stop_timestamp(self.__file_id)

    @property
    def curr_timestamp(self):
        """
        Provides the timestamp of the current reading position in the rec file
        in microseconds.

        :return: returns the current timestamp of the opened recording
        :rtype: long

        **1. Example:**

        .. python::
            REC_FILE = unicode(r"C:\\path\\to\\myrecording.rec")
            rec = RecFileReader()
            rec.open(REC_FILE)
            start_ts = rec.start_timestamp
            stop_ts = rec.stop_timestamp
            curr_ts = rec.curr_timestamp
            rec.close()
            print curr_ts
            52783468237
        """
        return rec.get_curr_timestamp(self.__file_id)

    @property
    def device_count(self):
        """
        Returns the number of devices which are inside the opened recording.

        :return: returns the number of devices of the opened recording
        :rtype: long

        **1. Example:**

        .. python::
            REC_FILE = unicode(r"C:\\path\\to\\myrecording.rec")
            rec = RecFileReader()
            rec.open(REC_FILE)
            count = rec.device_count
            rec.close()
            print count
            5
        """
        return rec.get_device_count(self.__file_id)

    def jump(self, timestamp):
        """
        Moves file pointer into the opened recording to special position
        specified by the timestamp.

        :param timestamp: timestamp in microseconds.
        :type timestamp:  long
        :return: returns True if it is able to jump to the specified timestamp
                 of the opened recording. Otherwise, this function returns False
        :rtype: boolean

        **1. Example:**

        .. python::
            rec.jump(234242234)
            True
        """
        return rec.jump(self.__file_id, timestamp)

    def read(self):
        """
        Reads the next available package from the opened rec file.

        :return: returns the data package if successful
        :rtype: array
        """
        return rec.read_package(self.__file_id, True)

    def check_file_support(self):
        """
        Checks if the opened rec file is supported by recfilereader.dll.

        :return: Returns True if the file is supported, otherwise False
        :rtype: boolean
        """
        return rec.check_file_support(self.__file_id)

    def device_property(self, device_index, prop_name):
        """
        Returns the value of a device property.

        :param device_index: the index of the device (data source).
        :type device_index: long
        :param prop_name: the name of the property
        :type prop_name: unicode
        :return: returns the value of a device property

        **1. Example:**

        .. python::
            rec.device_property(1, 'Name')
            5
        """
        return rec.get_device_property(self.__file_id, device_index, prop_name)

    def rec_property(self, prop_name):
        """
        Returns the value of a recording property.

        :param prop_name: the name of the property
        :type prop_name: unicode
        :return: returns the value of a recording property

        **1. Example:**

        .. python::
            rec.rec_property('GUID')
            {C34FD1A4-88F0-47A2-BE13-7B3B4E361E6F}
        """
        return rec.get_rec_property(self.__file_id, prop_name)

    def sys_property(self, prop_name):
        """
        Returns the property value of a system/MTS engine property.

        :param prop_name: the name of the property
        :type prop_name: unicode
        :return: returns the value of a system property
        """
        return rec.get_sys_property(self.__file_id, prop_name)

    def is_open(self):
        """
        Check if a recording is open.

        :return: Returns True if the recording is open, otherwise False is returned.
        :rtype: boolean
        """
        return rec.is_open(self.__file_id)


class Extractor(object):  # pylint:disable=R0902
    """
    recfile extractor wrapper around RecFileExtractor binary

    :deprecated: Replaced by `stk.mts.rfe.Rfe`
    """
    # format specifier
    JPG, BMP, AVI = list(range(3))

    def __init__(self, *args, **kwargs):
        """configure extractor exe, out path, video device and image channel

        :param args: argument list, whereas following keywords are covered
        :keyword rec_extractor: expecting 'path\\to\\RecFileExtractor.exe', default: (.\\rfe\\RecFileExtractor.exe)
        :keyword output_dir_path: path where images should be stored
        :keyword video_device: name of video device, e.g. 'mfc' for MFC31X or 'mfc4xx', default: None
        :keyword img_channel: examples: 'MFC3xx_long_image_right', 'MFC4xx_long_image_right', default: None
        """
        deprecation("Class stk.mts.rec.Extractor is deprecated, please use stk.mts.rfe.Rfe instead.")
        self._logger = Logger(self.__class__.__name__)
        self._logger.debug()

        # adapt to old, missing option extractor_path
        argnames, argoff = ["rec_extractor", "output_dir_path", "video_device", "img_channel"], 0
        for i in range(len(args)):
            if i == 0 and path.isdir(args[0]):
                argoff = 1
            kwargs[argnames[i + argoff]] = args[i]

        self._rec_extractor = kwargs.pop("rec_extractor",
                                         path.join(path.dirname(__file__), r'rfe\RecFileExtractor.exe'))
        self._outdir_pathname = kwargs.pop("output_dir_path", path.join(DEFAULT_OUTPUT_DIR_PATH,
                                                                        DEFAULT_GFX_OUTPUT_SUBDIR))

        # Create ouput folders
        if not path.exists(self._outdir_pathname):
            makedirs(self._outdir_pathname)
        else:  # or clean up existing one
            for entry in listdir(self._outdir_pathname):
                if path.isdir(path.join(self._outdir_pathname, entry)):
                    for fnam in listdir(path.join(self._outdir_pathname, entry)):
                        unlink(path.join(path.join(self._outdir_pathname, entry), fnam))
                    removedirs(path.join(self._outdir_pathname, entry))
                else:
                    unlink(path.join(self._outdir_pathname, entry))

        arg = kwargs.pop("video_device", None)
        self._video_device = "" if arg is None else ' /D:"' + arg + '"'
        arg = kwargs.pop("img_channel", None)
        self._channel = "" if arg is None else ' /C:"' + arg + '"'

        self._event_video_dir = None

    def Extract(self, recfile, start_ts, stop_ts=None, out_format=0):
        """
        - extracts just the images given by start_ts (integer/list) and stop_ts is none
        - extracts all images from start_ts to stop_ts when both of type integer
        - start_ts and stop_ts are of type list, then those indices refer multiple sequences to be extracted

        :param recfile: recording file name
        :param start_ts: start time stamp(s)
        :param stop_ts: stop / end time stamp(s)
        :param out_format: Extractor.JPG (default), Extractor.BMP, Extractor.AVI not yet supported
        """
        if out_format not in (Extractor.BMP, Extractor.JPG):
            self._logger.warning("given output format not supported.")
            return []

        if not path.isfile(recfile):
            self._logger.warning("file '%s' doesn't exist." % recfile)
            return []

        try:  # check available timestamps
            cdir = path.join(path.split(argv[0])[0], self._rec_extractor)
            sysret = Popen("%s %s /I%s" % (cdir, recfile, self._video_device),
                           shell=False, stdout=PIPE).communicate()[0]
        except OSError as ex:
            self._logger.warning("Couldn't verify timestamps: " + str(ex))
            return []

        times = research(r"StartTime:\s(\d*)\sStopTime:\s(\d*)(\r\n.*|$)", sysret)
        if times is not None and len(times.groups()) == 3:
            if isinstance(start_ts, six.integer_types):
                start_ts, stop_ts = [start_ts], [stop_ts]
            elif type(start_ts) == list and stop_ts is None:
                start_ts, stop_ts = start_ts, [None] * len(start_ts)
            img_list = []

            if type(start_ts) is not list:
                start_ts = [start_ts]

            if type(stop_ts) is not list:
                stop_ts = [stop_ts]

            for i_start, i_stop in zip(start_ts, stop_ts):
                try:
                    start = max(i_start, int(times.groups()[0]))
                    cmd = ('%s %s /O:"%s" /T:%d' % (cdir, recfile, self._outdir_pathname, start))
                    if i_stop is not None:
                        cmd += (' /U:%d' % max(start, min(i_stop, int(times.groups()[1]))))

                    cmd += self._video_device
                    cmd += self._channel
                    cmd += (' /F:bmp' if out_format == Extractor.BMP else '')

                    sysret = Popen(cmd, shell=False, stdout=PIPE).communicate()[0]
                except OSError as ex:
                    self._logger.warning("couldn't extract image " + str(ex))
                else:
                    err = research(r"Error:\s(.*)", sysret)
                    if err is not None and err.groups()[0] != '-1':
                        self._logger.warning(err.groups()[0])
                    else:
                        img_list.extend(findall(r"[Extract\sImage:|Already\sexisting:]\s((?i)\d*\.%s)\r" %
                                               ("bmp" if out_format == Extractor.BMP else "jpeg"), sysret))
            return img_list
        return []

    def SetOutputDirPath(self, output_dir):
        """sets the out dir, where to store the images
        """
        self._outdir_pathname = output_dir

        # Create ouput folders
        if not path.exists(self._outdir_pathname):
            makedirs(self._outdir_pathname)
        else:
            for entry in listdir(self._outdir_pathname):
                if path.isdir(path.join(self._outdir_pathname, entry)):
                    for fnam in listdir(path.join(self._outdir_pathname, entry)):
                        unlink(path.join(path.join(self._outdir_pathname, entry), fnam))
                    removedirs(path.join(self._outdir_pathname, entry))
                else:
                    unlink(path.join(self._outdir_pathname, entry))

    def MakeVideoDirPath(self, video_dir_path=None):
        """creates event video output folder
        """
        deprecation("non maintained method, please avoid using it, or you know what you're doing...")

        if video_dir_path is not None:
            self._event_video_dir = video_dir_path
        else:
            self._event_video_dir = path.join(self._outdir_pathname, SEQ_FOLDER_NAME)

        if not path.exists(self._event_video_dir):
            makedirs(self._event_video_dir)

    def SetRecFileExtractor(self, extractor_path):
        """sets the extractor executable path
        """
        self._rec_extractor = path.abspath(extractor_path)
        if not path.exists(self._rec_extractor):
            self._logger.error("Rec File Extractor path: '%s' doesn't exist." % self._rec_extractor)
            return False
        return True

    def SaveRecSeqFile(self, current_meas_file, video_list, start_timestamp,  # pylint: disable=R0912
                       seq_count, copy_files=False):
        """saves the file sequence
        """
        deprecation("non maintained method, please avoid using it, or you know what you're doing...")

        if not isinstance(video_list, list):
            self._logger.error("Expected instance of type 'list'. Instance of type '%s' found." % type(video_list))
            return None

        video_seq_file_path = path.join(self._event_video_dir, "%s_%s_%s%s" %
                                        (path.splitext(path.basename(current_meas_file))[0],
                                         str(start_timestamp), str(seq_count), SEQ_FILE_EXT))
        video_seq_dir_path = "SEQ" + str(start_timestamp) + "_" + str(seq_count)

        if copy_files:  # make the seq dir
            full_video_seq_dir_path = path.join(self._event_video_dir, video_seq_dir_path)
            if not path.exists(full_video_seq_dir_path):
                makedirs(full_video_seq_dir_path)

        try:
            fp = open(video_seq_file_path, "w")
        except IOError as ex:
            self._logger.exception(str(ex))
            return None

        plot_video_list = []
        try:
            for idx in range(len(video_list)):
                if idx != len(video_list) - 1:
                    fp.write(video_seq_dir_path + sep + path.basename(video_list[idx]) + "\n")
                else:
                    fp.write(video_seq_dir_path + sep + path.basename(video_list[idx]))

                plot_video_list.append(str(video_list[idx]))

                if copy_files:
                    copy(video_list[idx], full_video_seq_dir_path)

        except Exception as ex:
            self._logger.exception(str(ex))
            self._logger.error("Error while writting image sequence file: '%s'" % video_seq_file_path)
            video_seq_file_path = None
        finally:
            fp.close()

        # remove not necessary video files
        removed_timestamp_list = []
        for timestamp in video_list:
            if str(timestamp) not in plot_video_list:
                try:
                    if not timestamp in removed_timestamp_list:
                        remove(timestamp)
                        removed_timestamp_list.append(timestamp)
                except Exception as ex:
                    self._logger.exception(str(ex))

        return video_seq_file_path

# SMe: unused method?
#     def __extract_images(self, meas_file_path, index, from_timestamp, to_timestamp=None):
#         """unused method?
#         """
#         if not path.exists(meas_file_path):
#             self._logger.error("Measurement file doesn't exist: '%s'" % meas_file_path)
#             return None
#
#         if not path.exists(self._rec_extractor):
#             self._logger.error("Invalid rec file extractor path " + str(self._extractor_path))
#             return None
#
#         video_dir_path = path.join(self._event_video_dir, "SEQ" + str(from_timestamp) + "_" + str(index))
#
#         self.SetOutputDirPath(video_dir_path)
#
#         # extracted_timestamp_list = []
#         extracted_timestamp_list = self.GetImage(self._rec_extractor, meas_file_path, from_timestamp, to_timestamp)
#
#         if len(extracted_timestamp_list) == 0:
#             return None
#
#         image_timestamp_list = []
#         for image in extracted_timestamp_list:
#             try:
#                 timestamp = long(image.split('.jpeg')[0])
#                 image_timestamp_list.append(timestamp)
#             except ValueError:
#                 self._logger.error('while converting timestamp: %s.' % image)
#                 continue
#
#         if len(image_timestamp_list):
#             return image_timestamp_list
#
#         return None

    def GetImage(self, extractor_path, recfilepath, rel_start_timestamp,  # pylint: disable=R0912
                 rel_stop_timestamp=None, bmpFormat=False):
        """ Reads image from recording
        :param recfilepath: The path of the recording file.
        :param rel_start_timestamp: The relative timestamp of the first image.
        :param rel_stop_timestamp: The relative timestamp of the last image that is being extracted.
        :return: Path to the image file.
        """
        self._rec_extractor = path.abspath(extractor_path)

        return self.Extract(recfilepath, rel_start_timestamp, rel_stop_timestamp,
                            Extractor.BMP if bmpFormat else Extractor.JPG)

    def GetImageSequence(self, recfilepath, timestamps, is_list=True, bmpFormat=False):  # pylint: disable=R0912,R0915
        """ Reads image from recording
        :param: recfilepath: The path of the recording file.
        :param: timestamps: list of times images should be extracted from
        :param: is_list: indication whether timestamps list only contains 1 or 2 stamps
        :return: Path to the image file.
        """
        start_timestamp_list = []
        stop_timestamp_list = []
        if is_list is False:
            if len(timestamps) == 1:
                start_timestamp_list.append(timestamps[0])
                stop_timestamp_list.append(None)
            elif len(timestamps) > 1:
                start_timestamp_list.append(timestamps[0])
                stop_timestamp_list.append(timestamps[1])
            else:  # no timestamps in the list
                return []
        else:  # the timestamps is a list of individual image timestamps
            start_timestamp_list = timestamps
            stop_timestamp_list = [None] * len(start_timestamp_list)

        return self.Extract(recfilepath, start_timestamp_list, stop_timestamp_list,
                            Extractor.BMP if bmpFormat else Extractor.JPG)

"""
CHANGE LOG:
-----------
$Log: rec.py  $
Revision 1.3 2017/06/21 15:33:02CEST Mertens, Sven (uidv7805) 
as agreed with Jan-Hugo, we can use try / except around as no one is really using this module
Revision 1.2 2015/12/18 11:19:12CET Hospes, Gerd-Joachim (uidv8815)
update matching masks to new rfe 1.40,
some rfe tests adapted to new checksum and some new files in list
Revision 1.1 2015/04/23 19:04:38CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
Revision 1.25 2015/02/26 16:04:15CET Mertens, Sven (uidv7805)
adaptation for end time not being lower than start time
--- Added comments ---  uidv7805 [Feb 26, 2015 4:04:16 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.24 2014/12/08 18:15:10CET Ellero, Stefano (uidw8660)
Docstrings updated inside Python RecFile Reader module (rec.py) to reflect the fact that RecFileReader class methods accept 'unicode' string datatype instead of 'string' datatype.
--- Added comments ---  uidw8660 [Dec 8, 2014 6:15:10 PM CET]
Change Package : 288769:1 http://mks-psad:7002/im/viewissue?selection=288769
Revision 1.23 2014/10/10 14:16:45CEST Ellero, Stefano (uidw8660)
Documentation and examples for pyreccreader usage.
Revision 1.22 2014/10/10 13:46:18CEST Ellero, Stefano (uidw8660)
Documentation and examples for pyreccreader usage.
--- Added comments ---  uidw8660 [Oct 10, 2014 1:46:19 PM CEST]
Change Package : 245573:1 http://mks-psad:7002/im/viewissue?selection=245573
Revision 1.21 2014/10/10 12:28:47CEST Ellero, Stefano (uidw8660)
Documentation and examples for pyreccreader usage.
--- Added comments ---  uidw8660 [Oct 10, 2014 12:28:48 PM CEST]
Change Package : 245573:1 http://mks-psad:7002/im/viewissue?selection=245573
Revision 1.20 2014/07/25 16:39:25CEST Hecker, Robert (heckerr)
Add Epydoc description to some attributes.
--- Added comments ---  heckerr [Jul 25, 2014 4:39:25 PM CEST]
Change Package : 245561:1 http://mks-psad:7002/im/viewissue?selection=245561
Revision 1.19 2014/07/25 09:27:11CEST Hecker, Robert (heckerr)
Added support for RecFileReader Interface.
--- Added comments ---  heckerr [Jul 25, 2014 9:27:11 AM CEST]
Change Package : 245561:1 http://mks-psad:7002/im/viewissue?selection=245561
Revision 1.18 2014/05/12 09:48:00CEST Hecker, Robert (heckerr)
Added new JobSimFeature.
--- Added comments ---  heckerr [May 12, 2014 9:48:00 AM CEST]
Change Package : 236158:1 http://mks-psad:7002/im/viewissue?selection=236158
Revision 1.17 2014/03/27 12:36:22CET Hecker, Robert (heckerr)
Added backwardcompatibility.
--- Added comments ---  heckerr [Mar 27, 2014 12:36:23 PM CET]
Change Package : 227240:2 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.16 2014/03/24 21:44:20CET Hecker, Robert (heckerr)
Get Unit Test working again.
--- Added comments ---  heckerr [Mar 24, 2014 9:44:20 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.15 2014/03/24 21:08:09CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:09 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.14 2014/03/16 21:55:45CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:45 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.13 2014/02/21 14:31:23CET Mertens, Sven (uidv7805)
pylint -= 1
--- Added comments ---  uidv7805 [Feb 21, 2014 2:31:24 PM CET]
Change Package : 219923:1 http://mks-psad:7002/im/viewissue?selection=219923
Revision 1.12 2014/02/21 14:20:13CET Mertens, Sven (uidv7805)
removing duplicate code lines from image extraction methods,
introducing a more convinient method: Extract
--- Added comments ---  uidv7805 [Feb 21, 2014 2:20:13 PM CET]
Change Package : 219923:1 http://mks-psad:7002/im/viewissue?selection=219923
Revision 1.11 2014/02/20 14:10:11CET Mertens, Sven (uidv7805)
commenting out unused private method
--- Added comments ---  uidv7805 [Feb 20, 2014 2:10:12 PM CET]
Change Package : 219923:1 http://mks-psad:7002/im/viewissue?selection=219923
Revision 1.10 2014/02/20 09:44:35CET Mertens, Sven (uidv7805)
minor command line adaptation
--- Added comments ---  uidv7805 [Feb 20, 2014 9:44:36 AM CET]
Change Package : 219923:1 http://mks-psad:7002/im/viewissue?selection=219923
Revision 1.9 2014/02/05 20:24:26CET Hecker, Robert (heckerr)
BugFix: Removed Option /D for not used Device.
--- Added comments ---  heckerr [Feb 5, 2014 8:24:27 PM CET]
Change Package : 217367:1 http://mks-psad:7002/im/viewissue?selection=217367
Revision 1.8 2013/11/27 16:30:09CET Mertens, Sven (uidv7805)
cleanup
--- Added comments ---  uidv7805 [Nov 27, 2013 4:30:10 PM CET]
Change Package : 208576:1 http://mks-psad:7002/im/viewissue?selection=208576
Revision 1.7 2013/11/27 16:04:30CET Mertens, Sven (uidv7805)
update to work with V01.00.01 of RecFileExtractor
--- Added comments ---  uidv7805 [Nov 27, 2013 4:04:31 PM CET]
Change Package : 208576:1 http://mks-psad:7002/im/viewissue?selection=208576
Revision 1.6 2013/03/28 13:31:13CET Mertens, Sven (uidv7805)
minor pep8
Revision 1.5 2013/03/28 11:10:53CET Mertens, Sven (uidv7805)
pylint: last unused import removed
--- Added comments ---  uidv7805 [Mar 28, 2013 11:10:53 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/02/28 16:43:31CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguide.
--- Added comments ---  heckerr [Feb 28, 2013 4:43:31 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/28 08:12:08CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:09 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/27 16:19:51CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:51 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/13 09:36:19CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
Revision 1.6 2012/04/30 10:20:32CEST Mogos, Sorin (mogoss)
* update: added new methods to create image sequences
--- Added comments ---  mogoss [Apr 30, 2012 10:20:33 AM CEST]
Change Package : 104217:1 http://mks-psad:7002/im/viewissue?selection=104217
Revision 1.5 2011/06/30 13:27:25CEST Marius Dinu (DinuM)
added another optional constructor parameter for image channel
--- Added comments ---  DinuM [Jun 30, 2011 1:27:25 PM CEST]
Change Package : 68186:1 http://mks-psad:7002/im/viewissue?selection=68186
Revision 1.4 2010/10/18 13:30:07CEST Marius Dinu (DinuM)
Added " " to recfile path
--- Added comments ---  DinuM [Oct 18, 2010 1:30:08 PM CEST]
Change Package : 41612:12 http://mks-psad:7002/im/viewissue?selection=41612
Revision 1.3 2010/10/14 12:32:31CEST Marius Dinu (DinuM)
Added additional parameter to class constructor  for video device
--- Added comments ---  DinuM [Oct 14, 2010 12:32:31 PM CEST]
Change Package : 41612:12 http://mks-psad:7002/im/viewissue?selection=41612
Revision 1.2 2010/02/19 11:14:37CET dkubera
header and footer added
--- Added comments ---  dkubera [2010/02/19 10:14:37Z]
Change Package : 33974:2 http://LISS014:6001/im/viewissue?selection=33974
"""
