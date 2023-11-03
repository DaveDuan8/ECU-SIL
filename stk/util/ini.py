# -*- coding: iso-8859-1 -*-
"""
stk_ini
-------

Reading and Writing *.ini Files

:org:           Continental AG
:author:        Robert Hecker
                David Kubera

:version:       $Revision: 1.4 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/07/26 16:38:45CEST $
"""
# Import Python Modules -------------------------------------------------------
import re

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------
from stk.util.helper import deprecated


# Import Local Python Modules -------------------------------------------------

# Defines ---------------------------------------------------------------------
STRING_TARGET_ENCODING = "utf-8"
SCRIPT_ENCODING = "iso-8859-1"

# Classes ---------------------------------------------------------------------


class Ini(object):
    """
    Class which hase Base Methods for Reading and Writing Ini Files
    """
    __section = re.compile(r'^\[(.*)\]\s*')
    __key = re.compile(r'^([^\s]*)\s*=\s*(.*)$')

    # # The constructor.
    def __init__(self):
        """
        Initialize all unused Variables
        """
        self.__data = {}
        self.__file_path = ""

    # # The destructor.
    def __del__(self):
        self.__file_path = ""

    def __read(self):
        """
        Read the whole Ini File and creates the
        internal storage for the Ini File.

        :author:                 Robert Hecker
        """
        # Open File for Reading
        file_obj = file(self.__file_path)
        # initialize section
        sec = ""
        # read whole file and process it
        for line in file_obj:
            # decode and encode from mostly used windows
            # file encoding to standard py-script encoding
            # line = (line_tmp.decode(SCRIPT_ENCODING)).encode(STRING_TARGET_ENCODING)

            # Check after new Section [.....]
            match_obj = self.__section.match(line)
            if match_obj is not None:
                # Found new Section
                sec = str(match_obj.group(1))
                # Check if section is inside _data
                if sec not in self.__data:
                    # Add Section to _data
                    self.__data[sec] = {}
            else:
                # Found Key in Section
                match_obj = self.__key.match(line)
                if match_obj is not None:
                    # Found Key in Line
                    # get key and value
                    key, val = match_obj.group(1, 2)
                    self.__data[sec][str(key)] = val
        # close file
        file_obj.close()
        # delete file object
        del file_obj

    def write(self):
        """
        Write the whole Ini File to Disk. The FilePath which is
        used is either set by the Open Function or by the SetFilePath Function
        :autho:   Robert Hecker
        """
        # Write actual Dataset to ini File
        file_obj = file(self.__file_path, 'w')
        # Go through whole dataset and write data
        for section in self.__data:
            file_obj.write('[' + section + ']\n')
            for key in self.__data[section]:
                file_obj.write(key + '=' + str(self.__data[section][str(key)]) + '\n')
            file_obj.write('\n')

        # close file
        file_obj.close()
        # delete file object
        del file_obj

    def set_ini_path(self, file_path):
        """
        Set the Ini FilePath which must be used to Write the Ini File to Disk
        :author: Robert Hecker
        """
        self.__file_path = file_path

    def open(self, file_path):
        """
        Open the Ini File specified by Path, and read the whole Ini File
        into internal storage
        :author:  Robert Hecker
        """
        # store FilePath in Member Variable
        self.__file_path = file_path
        # Read Ini File
        self.__read()

    def write_key(self, section_name, key_name, value):
        """
        Set the Value specified by KeyName and SectionName to the Internal Ini
        File Storage. When SectionName or KeyName not exist, it will be created

        :param section_name:    [SectionName]
        :param key_name:        KeyName=...
        :param value:              ...=Value

        :author:               Robert Hecker
        """
        # Check if Section is insid _data
        if section_name not in self.__data:
            # Add Section to _data
            self.__data[section_name] = {}
        self.__data[section_name][str(key_name)] = value

    def read_key(self, section_name, key_name, default_value=0):
        """
        Read the Value specified by KeyName and SectionName from the Internal
        Ini File Storage. When SectionName or KeyName not exist, it will be
        created and filled with the Default Value. Value will be returned via
        return Value.

        :param section_name:    [SectionName]
        :param key_name:        KeyName=...
        :param default_value:        ..=Value
        :return:               Return value or default value
        :author:               Robert Hecker
        """
        # Check if Section is insid _data
        if section_name not in self.__data:
            self.write_key(section_name, key_name, default_value)

        if key_name not in self.__data[section_name]:
            self.write_key(section_name, key_name, default_value)

        return self.__data[section_name][str(key_name)]

    def get_sections(self):
        """
        Returns a list with the sections in the ini file.

        :return:               Returns list of sections or None
        :author:               Ovidiu Raicu
        """
        return list(self.__data.keys())

    def get_section_keys(self, section_name):
        """
        Returns a list of keys that bellong to the specified section

        :param section_name:   [section_name]

        :return:               Returns list of keys or None.
        :author:               Ovidiu Raicu
        """
        if section_name in self.__data:
            keys = []
            for item in self.__data[section_name]:
                keys.append(item)

            return keys
        else:
            return None

    def delete_key(self, section_name, key_name):
        """
        Returns a list of keys that bellong to the specified section

        :param section_name:   [section_name]
        :param key_name:       key_name=...

        :return:               Returns True if succesfull or False.
        :author:               Ovidiu Raicu
        """
        if section_name in self.__data:
            if key_name in self.__data[section_name]:
                del self.__data[section_name][key_name]
                return True
        return False

    @deprecated('write')
    def Write(self):  # pylint: disable=C0103
        """deprecated"""
        return self.write()

    @deprecated('set_ini_path')
    def SetIniPath(self, file_path):  # pylint: disable=C0103
        """deprecated"""
        return self.set_ini_path(file_path)

    @deprecated('open')
    def Open(self, file_path):  # pylint: disable=C0103
        """deprecated"""
        return self.open(file_path)

    @deprecated('write_key')
    def WriteKey(self, section_name, key_name, value):  # pylint: disable=C0103
        """deprecated"""
        return self.write_key(section_name, key_name, value)

    @deprecated('read_key')
    def ReadKey(self, section_name, key_name, default_value=0):  # pylint: disable=C0103
        """deprecated"""
        return self.read_key(section_name, key_name, default_value)

    @deprecated('get_sections')
    def GetSections(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_sections()

    @deprecated('get_section_keys')
    def GetSectionKeys(self, section_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_section_keys(section_name)

    @deprecated('delete_key')
    def DeleteKey(self, section_name, key_name):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_key(section_name, key_name)


"""
$Log: ini.py  $
Revision 1.4 2016/07/26 16:38:45CEST Mertens, Sven (uidv7805) 
move replacement
Revision 1.3 2016/07/26 16:14:20CEST Mertens, Sven (uidv7805)
return single backslashes
Revision 1.2 2016/05/23 10:38:17CEST Mertens, Sven (uidv7805)
we don't need to recode
Revision 1.1 2015/04/23 19:05:31CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.9 2015/01/23 21:44:17CET Ellero, Stefano (uidw8660)
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 23, 2015 9:44:18 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.8 2014/03/31 08:20:48CEST Hecker, Robert (heckerr)
Added backwardcompatiblity Methods.
--- Added comments ---  heckerr [Mar 31, 2014 8:20:48 AM CEST]
Change Package : 228290:1 http://mks-psad:7002/im/viewissue?selection=228290
Revision 1.7 2014/03/24 21:56:56CET Hecker, Robert (heckerr)
Adapted to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:56:56 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.6 2014/03/16 21:55:49CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:49 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.5 2013/03/05 15:50:42CET Hecker, Robert (heckerr)
Get Ini Class Full tested and Working.
--- Added comments ---  heckerr [Mar 5, 2013 3:50:42 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.4 2012/12/11 08:14:12CET Hecker, Robert (heckerr)
Removed stk Prefis from stkIni.
--- Added comments ---  heckerr [Dec 11, 2012 8:14:12 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2012/12/05 13:49:49CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:50 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 11:43:02CET Hecker, Robert (heckerr)
Update to pep8 styleguide.
--- Added comments ---  heckerr [Dec 5, 2012 11:43:05 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 18:01:46CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
