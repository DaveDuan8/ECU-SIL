"""
stk/mts/rfe
-----------

Classes for RecFileExtraction Functionalities

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.8 $
:date:          $Date: 2016/09/21 14:27:41CEST $
"""
import os
from subprocess import Popen, PIPE
from re import compile as rcompile, findall
from .. import error

# - import STK modules ------------------------------------------------------------------------------------------------
FILE_PATTERN = rcompile(r"[Extract\sImage:|Already\sexisting:]\s((?i)\d*\.\w{3,4})\r")
INFO_PATTERN = rcompile(r"StartTime:\s(\d+)\sStopTime:\s(\d+)")


# - classes -----------------------------------------------------------------------------------------------------------
class RfeError(error.StkError):
    """
    Exception Class for all RecFileEctractor Exceptions.

    :author:        Robert Hecker
    :date:          25.02.2014
    """
    def __init__(self, msg, errno=error.ERR_UNSPECIFIED):
        """
        Init Method of Exception class

        :param msg:   Error Message string, which explains the user was
                      went wrong.
        :type msg:    str
        :param errno: unique number which represents a Error Code inside the
                      Package.
        :type errno:  integer

        :author:      Robert Hecker
        :date:        04.09.2013
        """
        error.StkError.__init__(self, msg, errno)


class Rfe(object):
    """
    RecFileExtractor class which encapsulates the interface for the
    "RecFileExtractor.exe" binary.

    This class works as an wrapper, to call the RecFileExtractor.exe from python in a easy way.

    RecFileExtractor.exe is used to extract pictures (e.g. jpeg) or video (avi) from recordings
    and store them using the time stamps as name. Possible ouput formats are:

        - jpeg
        - bmp
        - avi
        - pgm
        - pfds

    (see RecFileExtractor.exe for more details:
     /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/ETK_EngineeringToolKit/04_Engineering/
     RFE_RecFileExtractor/04_Engineering/90_Distribute/bin/project.pj )

    **Example:**

    .. python::

        # Import stk.hpc
        from stk import mts

        #Create Instance from  RecFileExtractor class
        rfe = mts.Rfe('../../RecFileExtractor.exe')

        # Set the device
        rfe.device = 'mfc'

        # Set channel usage (optional)
        rfe.channel = "MFC3xx_long_image_right"

        # Set the output folder (optional)
        rfe.folder = r'./out'

        # Set Color usage (optional)
        rfe.color = True

        # Do the extraction
        img_name = rfe.extract_image('..path_to_recfile', 5959396274)


    :author:        Robert Hecker
    :date:          24.02.2014
    """
    def __init__(self, rec_file_extractor_path):  # pylint disable=R0902
        # R0902: this class needs more then 7 attributes,
        # they are prepared and passed as options to rfe.exe
        self.__path = None
        self.__set_path(rec_file_extractor_path)
        self.__start_timestamp = None
        self.__stop_timestamp = None
        self.__step_timestamp = None
        self.__format = 'jpeg'
        self.__codec = None
        self.__device = 'video'
        self.__channel = None
        self.__folder = None
        self.__color = False
        self.__brightup = None

    def __get_path(self):
        """ getter for property `path` """
        return self.__path

    def __set_path(self, value):
        """ setter for property `path` """
        if not os.path.exists(value):
            raise RfeError("RecFileExtractor path not Found: " + value)

        self.__path = value

    path = property(__get_path, __set_path)
    '''
    set/get the path for the "RecFileExtractor.exe"

    :type: str
    '''

    def __get_format(self):
        """ getter for property `format` """
        return self.__format

    def __set_format(self, value):
        """ setter for property `format` """
        self.__format = value

    format = property(__get_format, __set_format)
    """
    Set the format of the output files of the Extractor.
    possible formats are:

      - jpeg
      - bmp
      - avi
      - pgm
      - pfds

    :type: str
    """

    def __get_codec(self):
        """ getter for property `codec` """
        return self.__codec

    def __set_codec(self, value):
        """ setter for property `codec` """
        self.__codec = value

    codec = property(__get_codec, __set_codec)
    """
    set/get the codec to be used for avi fiel writing.

    :type: str
    :note: to get all supported codecs use: `list_codecs`
    """

    def __get_device(self):
        """ getter for property `device` """
        return self.__device

    def __set_device(self, value):
        """ setter for property `device` """
        self.__device = value

    device = property(__get_device, __set_device)
    """
    set/get the device name for extraction.
    Supported devices are:

      - csf
      - lpos
      - video
      - mfc

    :type: str
    """

    def __get_channel(self):
        """ getter for property `channel` """
        return self.__channel

    def __set_channel(self, value):
        """ getter for property `channel` """
        self.__channel = value

    channel = property(__get_channel, __set_channel)
    """
    set/get the channel name to be used for extraction.

    Channel could be channel names from MTS like
    "MFC3xx_short_image_left", "MFC3xx_Short_image_right",....

    Please replace " " in channels with "_"

    :type: str
    """

    def __get_folder(self):
        """
        Read only attribute to get the output `folder`
        of the RecFileExtractor Instance.

        :rtype: str
        """
        return self.__folder

    def __set_folder(self, value):
        """
        `folder` to store the output files.

        Folder should be absolute "c:/output"
        or relative "output/test"
        """
        self.__folder = value

    folder = property(__get_folder, __set_folder)
    """
    set/get the folder name where the images or avi's
    must be extracted to.
    When the Folder name doesn't exit, it will be created.
    Folder names can be absolute paths("c:/output"),
    or relative paths("output/test")

    :type: str
    """

    def __get_color(self):
        """ getter for property `color`

        :rtype: boolean
        """
        return self.__color

    def __set_color(self, value):
        """ getter for property `color` """
        self.__color = value

    color = property(__get_color, __set_color)
    """
    set/get the information, if images shall be extracted with color.
    When set to True, images will be extracted in Color with
    using the bayer decoding information.

    :type: bool
    """

    def __get_brightup(self):
        """ getter for property `brightup`

        :rtype: str
        """
        return self.__brightup

    def __set_brightup(self, value):
        """ getter for property `brightup` """
        self.__brightup = value

    brightup = property(__get_brightup, __set_brightup)
    """
    set/get the information if images shall be extracted with enhanced
    bightness settings.

    3 different settings are available:

      - "DO" for Downschift settings
      - "FD" Full Dynamic Algorithm.
      - "90" 90 % Dynamic Algorithm.

    :type: str
    """

    def __add_properties_to_cmd(self, cmd):
        """
        extend the cmd line string with the properties set by the useres,
        needed for extraction.

        :param cmd:    Part of CMD Line String without special parameters
        :type cmd:     str
        :return:       cmd line string
        :rtype:        str
        """

        if self.__start_timestamp is not None:
            cmd += ' /T:' + str(self.__start_timestamp)

        if self.__stop_timestamp is not None:
            cmd += ' /U:' + str(self.__stop_timestamp)

        if self.__step_timestamp is not None:
            cmd += ' /S:' + str(self.__step_timestamp)

        if self.__folder is not None:
            cmd += ' /O:' + str(self.__folder)

        if self.__format is not None:
            cmd += ' /F:' + self.__format

        if self.__codec is not None:
            cmd += ' /G:' + self.__codec

        if self.__device is not None:
            cmd += ' /D:' + self.__device

        if self.__channel is not None:
            cmd += ' /C:' + self.__channel

        if self.__color is not False:
            cmd += ' /R'

        if self.__brightup is not None:
            cmd += ' /B:' + self.__brightup

        return cmd

    def __build_and_execute(self, rec_file_path, info=False,
                            codec=False, device=False):
        """
        build the internal command, call the executable and do the error
        checking.

        :param rec_file_path: path to the input file.
        :type rec_file_path:  str
        :param info:          Flag if only the Start and StopTimestamp is
                              wanted.
        :type info:           boolean
        :param codec:         Flag if only a list of supported codecs is wanted.
        :type codec:          boolean
        :param device:        Flag if only a list of all included devices
                              is wanted.
        :type device:         boolean
        :return:              commandline shell output.
        :rtype:               str
        """

        cmd = str(self.__path) + ' "' + rec_file_path + '"'

        if codec:
            cmd = str(self.__path) + ' /L:C'
        elif device:
            cmd = str(self.__path) + ' "' + rec_file_path + '"' + ' /L:D'
        elif info:
            cmd += ' /I'
        else:
            cmd = self.__add_properties_to_cmd(cmd)

        proc = Popen(cmd, shell=False, stdout=PIPE)
        result = proc.communicate()[0]

        if proc.returncode != 0:
            msg = result + "File: {}".format(rec_file_path)
            code = proc.returncode
            raise RfeError(msg, code)
        # Popen.communicate buffer size is 4096bytes, and with RFE returning coninuous list of lines
        # communicate adds some '\f' while concatenating longer buffer content.
        # there are more clever solutions to read a continuous data flow, but here removing '\f' is enough
        return result.replace('\f', '')

    @staticmethod
    def __extract_file_names(cmd_output):
        """
        parse from a given input all image names, and return them as a list.

        :param cmd_output: textual output from RecFileExtractor.exe to parse
                           for image names.
        :type cmd_output:  str
        :return:           array of image file names
        :rtype:            list[str]
        """
        file_names = findall(FILE_PATTERN, cmd_output)

        return file_names

    @staticmethod
    def __extract_packet_abs_ts_info(cmd_output):
        """
        Parse from a given input the information regarding the absolute timestamp of the packet being extracted.

        :param cmd_output: textual output from RecFileExtractor.exe to parse
                           for info regarding the absolute timestamp of the
                           packet being extracted
        :type cmd_output:  str
        :return:           absolute timestamp info
        :rtype:            list[str]
        """
        timestamp = cmd_output.replace("Extract Info: ", "").split("\r")
        if "" in timestamp:
            timestamp.remove("")

        return timestamp

    @staticmethod
    def __extract_codecs(result):
        """
        parse from a given input all image names, and return them as a list.

        :param result: textual output from RecFileExtractor.exe to parse for
                       codecs.
        :type result:  str
        :return:       all supported codecs.
        :rtype:        dict{str:str,...}
        """
        codecs = {}
        search_next = True
        offset = result.find('\n') + 1
        offset = result.find('\n', offset) + 1
        offset = result.find('\n', offset) + 1
        while search_next:
            idx_end = result.find('\n', offset)
            key = result[offset: offset + 4]
            value = result[offset + 8: idx_end - 1]
            i = result.find('=', offset + 1)
            if idx_end < i:
                codecs[key] = value
                offset = idx_end + 1
            else:
                search_next = False

        return codecs

    @staticmethod
    def __extract_devices(result):
        """
        parse from a given input all devices and device classes,
        and return them as a list.

        :param result: textual output from RecFileExtractor.exe to parse for
                       devices.
        :type result:  str
        :return:       all included devices and device-classes.
        :rtype:        dict{str:str,...}
        """
        devices = {}
        import StringIO
        result2 = StringIO.StringIO(result)

        idx = 0
        for line in result2:
            if idx > 1:
                offset = line.find('\t')
                offset2 = line.find('\r')
                key = line[0:offset]
                if line[offset + 1] != '\t':
                    value = line[offset + 1:offset2]
                else:
                    value = line[offset + 2:offset2]
                if key in devices:
                    # Append
                    devices[key] = devices[key] + ";" + value
                else:
                    devices[key] = value
            idx += 1

        return devices

    def info(self, rec_file_path):
        """
        provide the start and stoptimestamp from the given recording.

        :param rec_file_path: path to the given rec file.
        :type rec_file_path:  str
        :return:              Start- and Stop-Timestamp in microseconds
        :rtype:               Tuple[Start_TS, Stop_TS]
        """
        result = self.__build_and_execute(rec_file_path, info=True)
        try:
            timestamps = findall(INFO_PATTERN, result)[0]
        except IndexError:
            return 0, 0

        start_timestamp = int(timestamps[0]) if timestamps[0] else 0
        stop_timestamp = int(timestamps[1]) if timestamps[1] else 0

        return start_timestamp, stop_timestamp

    def list_codecs(self):
        """
        list all supported codecs by the recfile extractor on this machine.

        With this method, you can list all supported codecs, which are
        installed on this pc. This codec information can be used to
        create avi files with a special compression format.

        :return:              All supported codecs
        :rtype:               dict{str:str}
        """
        result = self.__build_and_execute("", codec=True)
        return self.__extract_codecs(result)

    def list_devices(self, rec_file_path):
        """
        list all devices, which are inside the given recording.

        :param rec_file_path: path to the given rec file.
        :type rec_file_path:  str
        :return:              All supported codecs
        :rtype:               dict{str:str}
        """
        result = self.__build_and_execute(rec_file_path, device=True)
        return self.__extract_devices(result)

    def extract_image(self, rec_file_path, timestamp):
        """
        extract a image specified via timestamp from the ``*.rec`` file to disk.

        :param rec_file_path: path to the given rec file.
        :type rec_file_path:  str
        :param timestamp:     Timestamp of the wanted image in microseconds.
        :type timestamp:      int
        :return:              Name of the extracted image
        :rtype:               list[str]
        """
        self.__start_timestamp = timestamp
        result = self.__build_and_execute(rec_file_path)
        return self.__extract_file_names(result)

    def extract_images(self, rec_file_path, start_timestamp, stop_timestamp,
                       step_timestamp=None):
        """
        extract multiple images from a given recfile.
        All images between start_timestamp and stop_timestamp are extracted.
        When step_timestamp is specified, a minimum time between two images
        can be forced. This reduce the creation of images.

        :param rec_file_path:   path to the given rec file.
        :type rec_file_path:    str
        :param start_timestamp: start timestamp which is used for extraction.
        :type start_timestamp:  int [microseconds]
        :param stop_timestamp:  stop timestamp which is used for extraction.
        :type stop_timestamp:   int [microseconds]
        :param step_timestamp:  step timestamp which is used for extraction.
        :type step_timestamp:   int [microseconds]
        :return:                Names of the extracted images
        :rtype:                 list[str]
        """
        self.__start_timestamp = start_timestamp
        self.__stop_timestamp = stop_timestamp
        self.__step_timestamp = step_timestamp

        result = self.__build_and_execute(rec_file_path)
        return self.__extract_file_names(result)

    def create_avi(self, rec_file_path, start_timestamp, stop_timestamp, step_timestamp=None):
        """
        extract multiple images from a given recfile into one avi.

        All images between start_timestamp and stop_timestamp are extracted.
        When step_timestamp is specified, a minimum time between two images
        can be forced. This reduce the creation of images.

        :param rec_file_path:   path to the given rec file.
        :type rec_file_path:    str
        :param start_timestamp: start timestamp which is used for extraction.
        :type start_timestamp:  int [microseconds]
        :param stop_timestamp:  stop timestamp which is used for extraction.
        :type stop_timestamp:   int [microseconds]
        :param step_timestamp:  step timestamp which is used for extraction.
        :type step_timestamp:   int [microseconds]
        :return:                Names of the extracted images
        :rtype:                 list[str]
        """
        self.__start_timestamp = start_timestamp
        self.__stop_timestamp = stop_timestamp
        self.__step_timestamp = step_timestamp

        self.format = 'avi'
        result = self.__build_and_execute(rec_file_path)
        return self.__extract_file_names(result)

    def create_pfds(self, rec_file_path, start_timestamp, stop_timestamp,
                    step_timestamp=None):
        """
        Generates a PFDS file from a given recording file.
        All images between start_timestamp and stop_timestamp are considered.
        When step_timestamp is specified, a minimum time between two images
        can be forced.

        :param rec_file_path:   path to the given recording file.
        :type rec_file_path:    str
        :param start_timestamp: start timestamp which is used for extraction.
        :type start_timestamp:  int [microseconds]
        :param stop_timestamp:  stop timestamp which is used for extraction.
        :type stop_timestamp:   int [microseconds]
        :param step_timestamp:  step timestamp which is used for extraction.
        :type step_timestamp:   int [microseconds]
        :return:                info regarding the absolute timestamp of the packet being extracted
        :rtype:                 list[str]
        """
        self.__start_timestamp = start_timestamp
        self.__stop_timestamp = stop_timestamp
        self.__step_timestamp = step_timestamp

        result = self.__build_and_execute(rec_file_path)
        return self.__extract_packet_abs_ts_info(result)


"""
CHANGE LOG:
-----------
$Log: rfe.py  $
Revision 1.8 2016/09/21 14:27:41CEST Hospes, Gerd-Joachim (uidv8815) 
docfixes and test correction for avi
Revision 1.7 2016/09/21 13:57:29CEST Hospes, Gerd-Joachim (uidv8815)
pep8, epydoc fix
Revision 1.6 2016/09/21 13:30:34CEST Hospes, Gerd-Joachim (uidv8815)
adapt filter to list all files created by rfe
Revision 1.5 2016/06/16 15:58:53CEST Hospes, Gerd-Joachim (uidv8815)
pep8 pylint fixes
Revision 1.4 2016/06/14 17:42:10CEST Hospes, Gerd-Joachim (uidv8815)
rem. 'FF' bytes in Rfe output caused by coninuous stream (no add. tests, recfile too big),
simplify info() method
Revision 1.3 2016/05/09 11:00:20CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.2 2015/12/18 11:19:10CET Hospes, Gerd-Joachim (uidv8815)
update matching masks to new rfe 1.40,
some rfe tests adapted to new checksum and some new files in list
Revision 1.1 2015/04/23 19:04:38CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
Revision 1.11 2014/11/04 21:54:36CET Ellero, Stefano (uidw8660)
Extended RecFileExtractor unit tests.
--- Added comments ---  uidw8660 [Nov 4, 2014 9:54:36 PM CET]
Change Package : 270476:1 http://mks-psad:7002/im/viewissue?selection=270476
Revision 1.10 2014/09/03 13:55:25CEST Hecker, Robert (heckerr)
Added support for listing devices.
--- Added comments ---  heckerr [Sep 3, 2014 1:55:26 PM CEST]
Change Package : 261442:1 http://mks-psad:7002/im/viewissue?selection=261442
Revision 1.9 2014/07/25 16:14:58CEST Hecker, Robert (heckerr)
removed some pep8 messages.
--- Added comments ---  heckerr [Jul 25, 2014 4:14:59 PM CEST]
Change Package : 245561:1 http://mks-psad:7002/im/viewissue?selection=245561
Revision 1.8 2014/06/16 16:10:01CEST Hecker, Robert (heckerr)
BugFix for supporting RecFilePaths with whitespace in url.
--- Added comments ---  heckerr [Jun 16, 2014 4:10:02 PM CEST]
Change Package : 242889:1 http://mks-psad:7002/im/viewissue?selection=242889
Revision 1.7 2014/06/09 14:00:17CEST Hecker, Robert (heckerr)
Image Brightup Adaption.
--- Added comments ---  heckerr [Jun 9, 2014 2:00:18 PM CEST]
Change Package : 241755:1 http://mks-psad:7002/im/viewissue?selection=241755
Revision 1.6 2014/05/12 18:43:35CEST Hecker, Robert (heckerr)
updated example code.
--- Added comments ---  heckerr [May 12, 2014 6:43:36 PM CEST]
Change Package : 228373:1 http://mks-psad:7002/im/viewissue?selection=228373
Revision 1.5 2014/05/05 13:19:53CEST Hecker, Robert (heckerr)
Updated python wrapper to support Color Feature of RecFileExtractor.
--- Added comments ---  heckerr [May 5, 2014 1:19:54 PM CEST]
Change Package : 234596:1 http://mks-psad:7002/im/viewissue?selection=234596
Revision 1.4 2014/04/04 17:20:00CEST Hecker, Robert (heckerr)
Added Example to Rfe.
--- Added comments ---  heckerr [Apr 4, 2014 5:20:00 PM CEST]
Change Package : 227493:1 http://mks-psad:7002/im/viewissue?selection=227493
Revision 1.3 2014/03/20 16:14:00CET Hecker, Robert (heckerr)
BugFix in getting Codec.
--- Added comments ---  heckerr [Mar 20, 2014 4:14:00 PM CET]
Change Package : 221549:1 http://mks-psad:7002/im/viewissue?selection=221549
Revision 1.2 2014/03/16 21:55:57CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:57 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.1 2014/03/03 09:29:33CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
