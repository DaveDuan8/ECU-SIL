"""
stk/mts/cfg.py
--------------

Read MTS Config an write a sorted version
Class to sort the MTS Config file


:org:           Continental AG
:author:        Anne Skerl

:version:       $Revision: 1.3 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/04/04 13:48:01CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path
from re import split, match, sub as resub, MULTILINE, IGNORECASE
from collections import OrderedDict

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.logger import Logger
from stk.error import StkError

# - defines -----------------------------------------------------------------------------------------------------------
MODES = {'0': 'only sections = default',
         '1': 'sections + properties'}


# - functions ---------------------------------------------------------------------------------------------------------
def __split_strip_string(strng, delimiter, stripchars=' \'"'):
    """
    split input string at delimiters and remove
    stripchars from each split result.

    :param strng:      input string
    :type strng:       string
    :param delimiter:   delimiter where to split
    :type delimiter:   string
    :param stripchars: chars to strip
    :type stripchars:  string
    :return:           list of split and strip results
    :rtype:            list
    :author:           Anne Skerl
    :date:             27.06.2013
    """
    string_out = []
    for element in strng.split(delimiter):
        if len(element.strip(stripchars)) > 0:
            string_out.append(element.strip(stripchars))

    return string_out


def __get_sections(hfile, lines):
    """
    Get all Section out of the Lines, other lines are
    detected as HeaderLines, and will be written directly to the
    output file.

    :param hfile: Handle for outputfile
    :type hfile:  file
    :return:      found Sections
    :rtype:       dictionary
    :author:      Robert Hecker
    :date:        27.06.2013
    """

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
                hfile.write(line)  # write header lines

    return sections


def __sort_sections(hfile, sections, mode):
    """
    Sort the given sections regarding the mode, and write them to file.

    :param hfile: Handle for outputfile
    :type hfile:  file
    :return:      found Sections
    :rtype:       dictionary
    :author:      Robert Hecker
    :date:        27.06.2013
    """
    # sort sections
    sect_keys = list(sections.keys())
    sect_keys.sort()

    for key in sect_keys:
        # write section
        hfile.write('\n')
        hfile.write(key)

        if mode == 1:
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
                    raise StkError('error in properties in line %s!' % prop_line)

            # process properties
            if properties:
                # sort properties
                prop_keys = list(properties.keys())
                prop_keys.sort()

                # write properties
                for prop_key in prop_keys:
                    hfile.write(properties[prop_key])

        else:
            # write values per section
            vals = sections[key]
            for val in vals:
                if val[-1] == "\\":  # if value containes a list
                    hfile.write(val + '\t')  # then indent the line
                else:
                    hfile.write(val)


def sort(infile, outfile, mode):
    """
    Parse a give mts cfg file and sort it to be comparable with an ASCII
    File Compare Utility.

    :param infile:     Input File Path
    :type infile:      string
    :param outfile:    Output File Path
    :type outfile:     string
    :param mode:       0: Sort Section Only.
                       1: Sort Sections and Properties
    :type mode:        int
    :return:           -
    :rtype:            -
    :author:           Robert Hecker
    :date:             27.06.2013
    """
    # read infile
    file_in = file(infile)
    lines = file_in.readlines()
    file_in.close()

    # open outfile
    file_out = open(outfile, "w")

    sections = __get_sections(file_out, lines)

    # process sections
    if sections:
        __sort_sections(file_out, sections, mode)

    file_out.close()


# - classes -----------------------------------------------------------------------------------------------------------
class MtsCfgError(BaseException):
    """
    Base exception for MTS config issues
    """
    pass


class MtsSectionError(MtsCfgError):
    """
    Base exception for MTS config issues related to MO sections
    """
    pass


class MtsCfg(object):
    """
    Class to parse, create, modify and write MTS configuration files
    """

    def __init__(self, infile, outfile, logger):
        """
        Init instance of MtsCfg.

        :param infile: File's path to be parsed or None if not needed
        :type infile: str|unicode|None
        :param outfile: Path for the output file or None if not needed
        :type outfile: str|unicode|None
        :param logger: Custom logger
        :type logger: Logger

        :raise TypeError: In case 'infile' is None
        :raise IOError: Thrown by __parse_file() in case the given 'infile' does not exist or is unreadable.
        :raise BaseException: Thrown by __parse_file() in case there is any kind of unexpected situation while parsing.
        """
        super(MtsCfg, self).__init__()

        self.__infile = infile
        self.__outfile = outfile
        self.__logger = logger

        # The sections (or measurement objects) are stored in an ordered dictionary which is of convenience because of
        # the design limitation that they cannot have repeated names (tags).
        self._sections = OrderedDict()

        self._header = ""

        if infile:
            self.__parse_file()

    @property
    def mo_sections(self):
        """
        Provides all measurement objects currently contained in the model

        :return: Dict containing the MOs indexed by their names
        :rtype: dict[str, MtsCfgSection]

        """
        return self._sections

    @property
    def header(self):
        """
        Provides the current MTS configuration header (multi-line portion at the header of the file)

        :return: Plain string with the current header
        :rtype: basestring
        """
        return self._header

    @header.setter
    def header(self, value):
        """
        Sets/replaces the header

        :param value: Multi-line string to be set
        :type value: basestring
        """
        self._header = value

    def add_sections(self, *mo_sections):
        """Adds all given sections to the configuration

        :param mo_sections: Sections to be added
        :type mo_sections: tuple[MtsCfgSection]

        :raise MtsCfgError: In case one of the given sections' name is already used by an existing one
        """
        for mo_section in mo_sections:
            if mo_section.tag in self._sections:
                raise MtsCfgError("The model already contains a section called '{0}'.".format(mo_section.tag))
            self._sections[mo_section.tag] = mo_section

    def add_section(self, mo_section):
        """Adds a new section to the MTS configuration

        :param mo_section: The section to be added
        :type mo_section: MtsCfgSection

        :raise MtsCfgError: In case the given section's name is already used by an existing one
        """
        self.add_sections(mo_section)

    def remove_section(self, section_name):
        """Removes a section from the model

        :param section_name: The name of the section to be removed
        :type section_name: str

        :raise KeyError: Upon trying to remove a non-existing section
        """
        del self._sections[section_name]

    def write_to_file(self):
        """
        Writes the current state of the model into the 'outfile' path given in the __init__

        :raise TypeError: In case 'outfile' is None
        :raise IOError: In case the given 'outfile' to __init__

        """
        fdesc = open(self.__outfile, mode='w')
        self.__logger.info("Writing MTS cfg to file {0}...".format(path.abspath(self.__outfile)))
        fdesc.write(str(self))
        self.__logger.info("Successfully written. Closing file...")
        fdesc.close()
        self.__logger.info("File closed.")

    def __iter__(self):
        return self._sections.values().__iter__()

    def __unicode__(self):
        return self.__get_file_repr()

    def __str__(self):
        return str(self.__unicode__())

    def __ne__(self, other):
        self_ord_dict = OrderedDict(sorted(self.mo_sections.items()))
        other_ord_dict = OrderedDict(sorted(other.mo_sections.items()))

        return self.header != other.header or len(self.mo_sections) != len(other.mo_sections) or \
            any([a != b for a, b in zip(self_ord_dict.values(), other_ord_dict.values())]) or \
            any([a != b for a, b in zip(self_ord_dict, other_ord_dict)])

    def __eq__(self, other):
        return not self.__ne__(other)

    def __get_file_repr(self):
        """
        Provides the file representation for the model's current state
        """
        lines = list()
        lines.append(self._header + '\n')
        repl = lambda val: MtsCfg.__double_quote(val, True)

        for section in self.mo_sections.values():
            lines.append('\n')
            lines.append('[{tag}]\n'.format(tag=section.tag))
            for var, value in section.params.iteritems():
                lines.append('{var}='.format(var=var))
                if not isinstance(value, list):
                    lines.append(MtsCfg.__double_quote(value))
                else:
                    lines.append(',\\\n\t'.join([repl(i) for i in value]))
                lines.append('\n')

        return "".join(lines)

    def __parse_file(self):
        """
        Parses the 'infile' and fills the internal model

        :raise TypeError: In case 'infile' is None
        :raise IOError: In case the given 'infile' to __init__ does not exist or is unreadable.
        :raise BaseException: In case there is any kind of unexpected situation while parsing.
        """
        # Clear the storage just in case
        self._sections.clear()
        self._header = ""

        # TODO: Handle non-existent path
        file_text = open(self.__infile).read()

        # Split lines in sections
        for group in split(r'\n\s*\[', file_text, flags=MULTILINE):
            if match(r'.+\]', group):
                mo_section = self._create_section('[' + group)
                self.add_section(mo_section)
            else:
                if self._header:
                    raise BaseException("The header of the cfg was already stored.")
                # print group
                self._header = group

    @classmethod
    def _create_section(cls, string):
        """
        Creates a new section model

        :param string: The input string containing the section
        :type string: str | unicode
        :return: The generated MTS MO config for the given multi-line string
        :rtype: MtsCfgSection
        """
        return MtsCfgSection(string)

    @classmethod
    def __double_quote(cls, value, force_quotation=False):
        """TODO: explanation
        """
        if force_quotation or not match(r'^((0x[\da-f]+)|-?\d+)$', value, flags=IGNORECASE):
            return '"{val}"'.format(val=value)

        return value


class MtsCfgSection(object):
    """
    MTS config section class to model a measurement object (MO)
    """

    def __init__(self, string):
        """Init instance of MtsCfgSection

        :param string: MTS config-like multi-line string containing the MO definition
        :type string: str|unicode
        """
        super(MtsCfgSection, self).__init__()

        self._params = OrderedDict()
        self._tag = None
        self._logger = Logger(self.__class__.__name__)

        self._parse(string)

    def _parse(self, string):
        """
        Parses the given string and stores all information in the instance

        :param string: MTS config-like multi-line string containing the MO definition
        :type string: str|unicode
        """
        # Get MO tag. e.g. [SIM VFB]
        try:
            self._tag = match(r'\[(.+)\]\s*\n', string).group(1)
        except AttributeError:
            raise MtsSectionError("The given string to be parsed does not specify a correct tag for the section.")

        # Get body
        body = resub(r'\\\s*\n\s*', '', resub(r'.+\]\s*\n', '', string))
        sub = lambda value: resub(r'^"', '', resub(r'"$', '', value))

        # Get parameters from within the body
        params_list = split(r'\s*\n\s*', body)
        for param in params_list:
            # If not is an empty line
            if not match(r'\s*$', param):
                # print param
                var, values = match(r'^(.+?)=(.+)$', param).groups()

                # Split values into a list
                values_list = split(r',\s*', values)

                # Store the parameter
                self._add_param(var, [sub(i) for i in values_list])

    def _add_param(self, var, values_list):
        """Add a new parameter to the instance

        :param var: Name of the parameter
        :type var: str|unicode
        :param values_list: List of values for the given parameter
        :type values_list: list
        """
        self._params[var] = values_list if len(values_list) > 1 else values_list[0]

    @property
    def tag(self):
        """MO name
        """
        return self._tag

    @property
    def params(self):
        """Dict of parameters
        """
        return self._params

    @property
    def mo_class(self):
        """Class name of the MO. None if not known.
        """
        try:
            return self._params["Class"]
        except KeyError:
            self._logger.info("Section {tag} does not provide 'Class' info".format(tag=self.tag))

        return None

    def __getitem__(self, item):
        return self.params[item]

    def __len__(self):
        return len(self.params)

    def __iter__(self):
        return self.params.__iter__()

    def __str__(self):
        return self.tag + ": " + str(self.params)

    def __ne__(self, other):
        return self.tag != other.tag or self.params != other.params

    def __eq__(self, other):
        return not self.__ne__(other)


r"""
Log:
$Log: cfg.py  $
Revision 1.3 2016/04/04 13:48:01CEST Mertens, Sven (uidv7805) 
pylinting
Revision 1.2 2015/09/25 14:30:25CEST Hospes, Gerd-Joachim (uidv8815)
fix parse error at '\ ' (space after \)
--- Added comments ---  uidv8815 [Sep 25, 2015 2:30:25 PM CEST]
Change Package : 358695:1 http://mks-psad:7002/im/viewissue?selection=358695
Revision 1.1 2015/04/23 19:04:37CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
Revision 1.6 2015/03/06 14:27:46CET Mertens, Sven (uidv7805)
fix wrong overwrite
--- Added comments ---  uidv7805 [Mar 6, 2015 2:27:47 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.5 2015/03/06 13:45:24CET Mertens, Sven (uidv7805)
exchanging logger, removing doc errors
--- Added comments ---  uidv7805 [Mar 6, 2015 1:45:25 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.4 2014/12/03 17:02:43CET Hecker, Robert (heckerr)
Added additional Config Parser code needed by Alejandro.
--- Added comments ---  heckerr [Dec 3, 2014 5:02:44 PM CET]
Change Package : 287741:1 http://mks-psad:7002/im/viewissue?selection=287741
Revision 1.3 2014/03/24 21:08:07CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:08 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.2 2014/03/16 21:55:49CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:50 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.1 2013/06/27 16:01:40CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
