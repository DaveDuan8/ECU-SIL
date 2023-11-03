"""
stk/mts/bpl
-----------

Read MTS Config an write a sorted version
Class to sort the MTS Config file


:org:           Continental AG
:author:        Anne Skerl

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/04/04 13:48:01CEST $
"""
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os.path import isfile
from optparse import OptionParser

# - import STK modules -------------------------------------------------------------------------------------------------
from stk.util.logger import Logger, INFO
from stk.util.helper import deprecated

# - defines ------------------------------------------------------------------------------------------------------------
MODES = {'0': 'only sections = default',
         '1': 'sections + properties'}


# - functions ----------------------------------------------------------------------------------------------------------
def split_strip_string(strng, delimiter, stripchars=' \'"'):
    """
    split input string at delimiters and remove
    stripchars from each split result

    @param strng:        input string
    @param delimiter:     delimiter where to split
    @param stripchars:    chars to strip

    @return string_out:   list of split and strip results
    """

    string_out = []
    for element in strng.split(delimiter):
        if len(element.strip(stripchars)) > 0:
            string_out.append(element.strip(stripchars))

    return string_out


# - classes ------------------------------------------------------------------------------------------------------------
class MtsConfig(object):
    """ Classes to handle the MTS Configuration Files
    """
    def __init__(self, infile, outfile, logger):
        """
        Init MTS Configuration

        @param infile:      file to sort
        @param outfile:     file to write after sorting

        """
        self.__infile = infile
        self.__outfile = outfile
        self.__logger = logger

    def sort(self, mode):
        """
        sort sections and in each section sorts properties

        Mode 0: only sections
        Mode 1: sections and properties

        @param mode: sort mode: sort only sections ['0'], sections + properties ['1']
        """
        # read infile
        file_obj = file(self.__infile)
        lines = file_obj.readlines()
        file_obj.close()

        # open outfile
        fobj = open(self.__outfile, "w")

        # find sections
        section = ''
        sections = {}
        for line in lines:
            if len(line.strip()) > 0:  # ignore empty lines
                # line is section start
                if line.startswith('['):
                    section = line

                # line is property
                elif section:
                    if section in sections:
                        # append to  sections-entry
                        sections[section].append(line)
                    else:
                        # start new sections-entry
                        sections[section] = [line, ]

                # line is header
                else:
                    fobj.write(line)  # write header lines

        # process sections
        if sections:
            # sort sections
            sect_keys = list(sections.keys())
            sect_keys.sort()

            for key in sect_keys:
                # write section
                fobj.write('\n')
                fobj.write(key)

                if mode == '1':
                    # find properties
                    prop = ''
                    properties = {}
                    for prop_line in sections[key]:
                        prop_split = prop_line.split('=', 1)
                        if len(prop_split) > 1:
                            prop = prop_split[0]
                            properties[prop] = prop_line
                        elif prop in properties:
                            properties[prop] += prop_line
                        else:
                            self.__logger.error('error in properties in line ' + str(prop_line) + '!')

                    # process properties
                    if properties:
                        # sort properties
                        prop_keys = list(properties.keys())
                        prop_keys.sort()

                        # write properties
                        for prop_key in prop_keys:
                            fobj.write(properties[prop_key])

                else:
                    # write values per section
                    vals = sections[key]
                    for val in vals:
                        if val[-1] == "\\":  # if value containes a list
                            fobj.write(val + '\t')  # then indent the line
                        else:
                            fobj.write(val)

        fobj.close()
        self.__logger.info("Written to %s" % self.__outfile)

    @deprecated('sort')
    def Sort(self, mode):  # pylint: disable=C0103
        """deprecated"""
        return self.sort(mode)


def main():
    """main function"""
    logger = Logger(str(sys._getframe().f_code.co_name), INFO)

    # Parse command line parameters
    tmp = 'usage: %prog [options] <cfg_files_in> \n   with <cfg_files_in> = '
    tmp += '"<path\\filename>, <path\\filename>, ..."'
    optparser = OptionParser(usage=tmp)
    tmp = "The output files to write. [default=<cfg_file_in>_sorted.cfg]"
    optparser.add_option("-o", "--out-file", dest="outfiles", help=tmp)
    tmp = "The sort mode to use. [0 = default = only sections, 1 = sections + properties]"
    optparser.add_option("-m", "--mode", dest="mode", default='0', help=tmp)

    cmd_options = optparser.parse_args()

    if not cmd_options[1]:
        # call help
        optparser.print_help()
    else:
        # prepare infiles
        infiles = split_strip_string(cmd_options[1][0], ',')

        if cmd_options[0].mode not in list(MODES.keys()):
            logger.error("Sort mode %s unknown, possible modes: \n %s!" % (cmd_options[0].mode, MODES))
        else:

            # prepare outfiles
            if cmd_options[0].outfiles is None:
                outfiles = []
            else:
                outfiles = split_strip_string(cmd_options[0].outfiles, ',')

            # start
            for filecount in range(len(infiles)):
                logger.info("Start sorting file %d: %s\n   ..." % (filecount, infiles[filecount]))
                # outfile name
                if not outfiles or (len(outfiles) < filecount + 1):
                    split_result = infiles[filecount].rsplit('.', 1)
                    outfiles.append(split_result[0] + '_sorted.' + split_result[1])

                # check outfile name
                if outfiles[filecount] in infiles:
                    # never overwrite infiles
                    logger.error('Overwrite existing infile is not allowed: %s.' % infiles[filecount])
                    # exc_type, exc_value, exc_traceback = sys.exc_info()
                    logger.error('The original problem occured here: %s' % str(sys.exc_info()))
                    raise IOError('Overwrite existing infile is not allowed: %s.' % infiles[filecount])

                elif isfile(outfiles[filecount]):
                    # ask to overwrite if oufile already exists
                    print('   You are going to overwrite the file %s.' % outfiles[filecount])
                    print('   Do you really want to continue?')
                    go_on = str(input('   press Enter to continue or any key to break\n'))
                    if go_on:
                        print('stopped by user')
                        continue

                # sorting
                mts_cfg = MtsConfig(infiles[filecount], outfiles[filecount], logger)
                mts_cfg.sort(cmd_options[0].mode)

            # done
            logger.info("Done.")

# Main Entry Point ------------------------------------------------------------
if __name__ == '__main__':
    """
    parameter example:

    #define 2 output file names, give 4 input file names
    -> last 2 files get default ending at output file
    -o "D:/CGEB/file1_out.cfg, D:/CGEB/file2_out.cfg" "D:/CGEB/file1.cfg,
    D:/CGEB/file2.cfg, D:/CGEB/file3.cfg, D:/CGEB/file4.cfg"
    """
    main()


"""
Log:
$Log: cfg_base.py  $
Revision 1.2 2016/04/04 13:48:01CEST Mertens, Sven (uidv7805) 
pylinting
Revision 1.1 2015/04/23 19:04:36CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
Revision 1.11 2015/02/09 18:26:59CET Ellero, Stefano (uidw8660)
Removed all mts based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Feb 9, 2015 6:26:59 PM CET]
Change Package : 301800:1 http://mks-psad:7002/im/viewissue?selection=301800
Revision 1.10 2014/03/24 21:08:06CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:07 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.9 2014/03/16 21:55:47CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:48 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.8 2013/04/02 10:25:01CEST Mertens, Sven (uidv7805)
pylint: E0213, E1123, E9900, E9904, E1003, E9905, E1103
--- Added comments ---  uidv7805 [Apr 2, 2013 10:25:02 AM CEST]
Change Package : 176171:9 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.7 2013/03/28 15:25:22CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:22 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/01 16:00:53CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 4:00:56 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/28 08:12:17CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:17 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/27 16:19:54CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:54 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/26 20:21:28CET Raedler, Guenther (uidt9430)
- Updates for Peps8 StyleGuide
--- Added comments ---  uidt9430 [Feb 26, 2013 8:21:28 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/14 15:38:10CET Raedler, Guenther (uidt9430)
- fixed logger error
--- Added comments ---  uidt9430 [Feb 14, 2013 3:38:10 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
------------------------------------------------------------------------------
-- From cgeb_base archive
------------------------------------------------------------------------------
Revision 1.3 2011/02/17 16:42:13CET Skerl, Anne (uid19464)
*update: add mode option to sort also properties (=elements) inside sections -
but do not mix order in connection def. lists
*update: change order of input checks and logging outputs
--- Added comments ---  uid19464 [Feb 17, 2011 4:42:14 PM CET]
Change Package : 38933:7 http://mks-psad:7002/im/viewissue?selection=38933
Revision 1.2 2011/02/15 15:48:46CET Skerl Anne (uid19464) (uid19464)
*add possibility to sort several files at once
*check if outfile exists and ask what to do
--- Added comments ---  uid19464 [Feb 15, 2011 3:48:46 PM CET]
Change Package : 38933:7 http://mks-psad:7002/im/viewissue?selection=38933
Revision 1.1 2011/02/11 15:54:51CET Skerl Anne (uid19464) (uid19464)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/Base_CGEB
/06_Algorithm/04_Engineering/02_Development_Tools/scripts/project.pj
"""
