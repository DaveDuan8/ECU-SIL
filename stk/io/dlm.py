"""
dlm_read
--------

Script to read signal values from the simulation output delimited files.

:org:           Continental AG
:author:        Marius Dinu

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/03/31 16:36:27CEST $
"""
# pylint: skip-file
# =====================================================================================================================
# Imports
# =====================================================================================================================
from os import path
from csv import Error, reader
from logging import debug, warning
from re import match
import numpy as np

from stk.util.helper import deprecation


class Reader(object):
    """
    This class is deprecated, please use SignalReader instead!

    **Delimited reader class**

    usage (example)
    ---------------

    .. python::
        reader = stk.io.dlm.Reader(<file_path>,
                                   'delim'=<delimiter>,
                                   'scan_type'=<'prefetch','no_prefetch'>,
                                   'scan_opt'=<'scan_auto','scan_raw','scan_force'>,
                                   'header_opt'=<'header','no_header'>,
                                   'skip_lines'=<number_of_header_lines_to_skip>,
                                   'skip_data_lines'=<number_of_data_lines_to_skip>,
                                   'type'=<np.float32,'float','long'>
                                  )

    Examples:

    .. python::
        import numpy as np
        import stk.io.dlm

        # EXAMPLE 1
        stk_dlm = stk.io.dlm.Reader('file_hla_xyz',delim ='\t',scan_type='NO_PREFETCH')
        # read all signals
        signals = reader.read_signals_values()
        # get values
        read_values = stk_dlm.get_signal_by_name('lux_R2G')

        # EXAMPLE 2
        stk_dlm = stk.io.dlm.Reader('file_sla_xyz.csv',
                                    delim =',',
                                    scan_type='NO_PREFETCH',
                                    skip_lines=8)
        # read only signal 'timestamp'
        stk_dlm.read_signals_values('timestamp')
        # get signal
        values = stk_dlm.get_signal_by_name('timestamp')

        # EXAMPLE 3
        instance_ARS = stk.io.dlm.Reader('file_ars_xyz.csv',
                                         scan_type='PREFETCH')
        instance_ARS.get_signal_by_name('Time stamp')

        # EXAMPLE 4
        ARS_signals_of_interrest_list = ['Time stamp','Cycle counter']
        instance_ARS = stk.io.dlm.Reader('file_ars_xyz.csv',
                                          delim =';',
                                          scan_type='NO_PREFETCH',
                                          scan_opt = 'scan_raw')
        signals_ARS = instance_ARS.read_signals_values(ARS_signals_of_interrest_list)

        # EXAMPLE 5
        instance_ARS = stk.io.dlm.Reader('file_ars_xyz.csv',
                                         delim =';',
                                         scan_type='NO_PREFETCH',
                                         scan_opt = 'scan_force',
                                         type = np.float32)

    """
    def __init__(self, file_path=None, **kwargs):
        """Reader
        """
        deprecation('Class "BsigReader" is deprecated use "SignalReader" instead')
        self.__file_path = file_path.rstrip()
        self.__signal_names = []
        self.__sigValDict = {}
        self.__sigTypDict = {}
        self.__sigIdxDict = {}
        self.__kwargs = kwargs
        self.__option_map = {'delim': [';', ',', '\t', ' '], 'scan_type': ['prefetch', 'no_prefetch'],
                             'scan_opt': ['scan_auto', 'scan_raw', 'scan_force'],
                             'header_opt': ['header', 'no_header']}

        # self.__special_values_map = {'1.#IN': numpy.inf,'-1.#IN':-numpy.inf}
        self.__file_header = []

        accepted_options_list = ['delim', 'scan_type', 'scan_opt', 'header_opt',
                                 'skip_lines', 'skip_data_lines', 'type']

        for opt in self.__kwargs:
            if opt.lower() not in accepted_options_list:
                raise StandardError('Option "%s" specified,possible values for class constuctor parameters are %s' %
                                    (opt, accepted_options_list))

        if 'delim' in self.__kwargs:
            if self.__kwargs['delim'].lower() in self.__option_map['delim']:
                self.__delimiter = self.__kwargs['delim']
            else:
                raise StandardError('Delimiter "%s" specified,possible values for "delim" are %s' %
                                    (self.__kwargs['delim'], self.__option_map['delim']))
        else:
            self.__delimiter = ";"

        if 'skip_lines' in self.__kwargs:
            self.__skip_lines = self.__kwargs['skip_lines']
        else:
            self.__skip_lines = 0

        if 'skip_data_lines' in self.__kwargs:
            self.__skip_data_lines = self.__kwargs['skip_data_lines']
        else:
            self.__skip_data_lines = 0

        if 'scan_type' in self.__kwargs:
            if self.__kwargs['scan_type'].lower() in self.__option_map['scan_type']:
                self.__scan_type = self.__kwargs['scan_type']
            else:
                raise StandardError('Scan type "%s" specified,possible values for "scan_type" are %s' %
                                    (self.__kwargs['scan_type'], self.__option_map['scan_type']))
        else:
            self.__scan_type = 'PREFETCH'

        if 'scan_opt' in self.__kwargs:
            self.__scan_opt = self.__kwargs['scan_opt']
            if self.__scan_opt.lower() == "scan_force":
                if 'type' in self.__kwargs:
                    self.__desired_type = self.__match_type(self.__kwargs['type'])
                else:
                    raise StandardError('Scan option %s specified, but no type option specified' % (self.__scan_opt))
        else:
            self.__scan_opt = 'scan_auto'

        if 'header_opt' in self.__kwargs:
            if self.__kwargs['header_opt'].lower() in self.__option_map['header_opt']:
                self.__header_opt = self.__kwargs['header_opt']
            else:
                raise StandardError('header_opt "%s" specified,possible values for "header_opt" are %s' %
                                    (self.__kwargs['header_opt'], self.__option_map['header_opt']))
        else:
            self.__header_opt = 'header'

        if self.__file_path is not None and path.isfile(self.__file_path):
            if self.__scan_type.lower() == 'prefetch':
                self.read_signals_values()
            else:
                self.get_file_header()
        else:
            raise StandardError('"%s" not found ' % (self.__file_path))

    def set_file_path(self, file_path):
        self.__file_path = file_path
        self.__signal_names = []
        self.__sigValDict = {}
        self.__sigTypDict = {}
        self.__sigIdxDict = {}

    def __open_file(self, file_path):
        if path.isfile(file_path):
            debug("Reading signals values from file '%s'..." % self.__file_path)
            csv_file = open(file_path, "r")
            return csv_file
        else:
            raise TypeError("Expected instance of type file, but found instance of '%s' and '%s'instead." %
                            type(file_path) % type(file_path))
            return None

    def __getSigValType(self, value):
        """
        Returns the type of the signal values

        :param value:  The value of the signal that is being converted
        """

        if (match(r"^(\d+)$", value.lstrip()) is not None):
            return long
        elif(match(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?\s*\Z", value.lstrip()) is not None):
            return float
        else:
            return str

    def __match_type(self, inType):
        """
        Parse input arg strings like 'long' and 'float' to regarding types.
        It's better to use types directly like : np.float32 or type(float(0))

        :param inType:  input type or type string
        """
        if inType == np.float32:
            return input
        if inType == 'long':
            return type(long(0))
        if inType == 'float':
            return type(float(0.0))
        return inType

    def __match_special_value(self, value):
        if (match(r"[+]?1(\.)[#][Ii][Nn]", value.lstrip()) is not None):
            return np.inf
        elif (match(r"-1(\.)[#][Ii][Nn]", value.lstrip()) is not None):
            return -np.inf
        return

    def get_signal_value_type(self, signal_name):
        """
        Returns the type of the signal values

        :param signal_name:     The name of the signal for which the request was performed
        :return: type of named signal or None
        """
        if signal_name in self.__sigTypDict:
            return self.__sigTypDict[signal_name]
        return None

    def read_signals_values(self, signals_list=None):
        """
        Reads signal values from a simulation file - csv format.
        This function reads a list of signal given as input.
        When signals_list is 'None' all signal will be read

        :param signals_list:   the list of the signals
        :return: dictionary with extracted signals, empty {} in case of errors
        """
        if isinstance(signals_list, str):
            signals_list = [signals_list]
        # Open file
        csv_file = self.__open_file(self.__file_path)
        if csv_file is not None:
            csv_reader = reader(csv_file, delimiter=self.__delimiter)
            # if skip_lines constructor parameter is not specified
            for i in range(self.__skip_lines):
                csv_reader.next()
            # get all signals name
            self.__file_header = csv_reader.next()
            if (self.__file_header.count('') > 0):
                self.__file_header.remove('')

            # watch for leading spaces in signal_list_names
            for i in range(len(self.__file_header)):
                self.__file_header[i] = self.__file_header[i].lstrip()

#            if self.__header_opt == 'no_header':
#                csv_reader.next()
            # if skip_data_lines constructor parameter is  specified
            for i in range(self.__skip_data_lines):
                csv_reader.next()

            if signals_list is not None:
                for signal_name in signals_list:
                    if self.__file_header.count(signal_name) == 1:
                        # avoid duplicates
                        if self.__signal_names.count(signal_name) == 0:
                            self.__signal_names.append(signal_name)
                        else:
                            # this should never happened
                            warning("Signal name: '%s' duplicated!" % signal_name)
                    else:
                        warning("Signal name: '%s' not found in '%s'" % (signal_name, self.__file_path))
            else:
                self.__signal_names = self.__file_header

            # print self._signal_names
            for signal_name in self.__signal_names:
                if (self.__file_header.count(signal_name) == 1):
                    self.__sigIdxDict[signal_name] = self.__file_header.index(signal_name)
                    self.__sigValDict[signal_name] = []

#            index = 0
            if self.__header_opt == 'header':
                if self.__scan_opt == 'scan_raw':
                    self.__read_signals_raw(csv_reader)
                elif self.__scan_opt == 'scan_auto':
                    self.__read_signals_auto(csv_reader)
                else:
                    self.__read_signals_forced_type(csv_reader, self.__desired_type)
            else:
                if self.__scan_opt == 'scan_raw':
                    self.__read_signals_raw_no_header(csv_reader)
                elif self.__scan_opt == 'scan_auto':
                    self.__read_signals_auto_no_header(csv_reader)
                else:
                    self.read_signals_forced_type_no_header(csv_reader, self.__desired_type)
            del csv_reader
            csv_file.close()
            # print timer.GetDuration()
        else:
            # close file
            # del csv_reader
            csv_file.close()

            if len(self.__sigValDict) == 0:
                return None

        debug("Signal(s) values reading done...")
        # Done
        return self.__sigValDict

    def __read_signals_raw(self, csv_obj):
        try:
            for row in csv_obj:
                for signal in self.__signal_names:
                    try:
                        self.__sigValDict[signal].append(str(row[self.__sigIdxDict[signal]]))
                    except IndexError:
                        # warning here
                        self.__sigValDict[signal].append(' ')
        except Error, e:
            print 'file %s, line %d: %s' % (self.__file_path, csv_obj.line_num, e)
#            del csv_reader
#            csv_file.close()
            self.__sigValDict = {}
            return None
        # print timer.GetDuration()
        return self.__sigValDict

    def __read_signals_auto(self, csv_obj):
        try:
            # go through signal value list
            signal_type_retrived = False
            signal_flag = False
#            i = 0
            for row in csv_obj:
                for signal in self.__signal_names:
                    if not signal_type_retrived:
                        try:
                            self.__sigTypDict[signal] = self.__getSigValType(row[self.__sigIdxDict[signal]])
                            signal_flag = True
                        except IndexError:
                            signal_flag = False
                            self.__sigTypDict[signal] = type(float)
                    try:
                        self.__sigValDict[signal].append(self.__sigTypDict[signal](row[self.__sigIdxDict[signal]]))
                    except IndexError:
                        signal_flag = False
                        self.__sigValDict[signal].append(None)
                    except ValueError:
                        if len(row[self.__sigIdxDict[signal]]) != 0:
                            if self.__match_special_value(row[self.__sigIdxDict[signal]]) is not None:
                                (self.__sigValDict[signal].append(self.__sigTypDict[signal]
                                 (self.__match_special_value(row[self.__sigIdxDict[signal]]))))
                            else:
                                # the type of the signal must have been determined wrong
                                # at the first pass through the row
                                self.__sigTypDict[signal] = self.__getSigValType(row[self.__sigIdxDict[signal]])
                                (self.__sigValDict[signal].append(self.__sigTypDict[signal]
                                 (row[self.__sigIdxDict[signal]])))
                        else:
                            self.__sigValDict[signal].append(None)
                signal_type_retrived = signal_flag
        except Error, e:
            print 'file %s, line %d: %s' % (self.__file_path, csv_obj.line_num, e)
#             del csv_reader
#             csv_file.close()
            self.__sigValDict = {}
            return None

        return self.__sigValDict

    def __read_signals_forced_type(self, csv_obj, desired_type):
        try:
            for row in csv_obj:
                for signal in self.__signal_names:
                    try:
                        self.__sigValDict[signal].append(self.__desired_type(row[self.__sigIdxDict[signal]]))
                    except IndexError:
                        self.__sigValDict[signal].append(' ')
                    except ValueError:
                        self.__sigValDict[signal].append(None)
                        raise ValueError('Cannot covert Signal "%s", to type  "%s"' % (signal, self.__desired_type))
        except Error, e:
            print 'file %s, line %d: %s' % (self.__file_path, csv_obj.line_num, e)
#            del csv_reader
#            csv_file.close()
            self.__sigValDict = {}
            return None
        return self.__sigValDict

    def __read_signals_raw_no_header(self, csv_obj):
        # data_matrix = numpy.array([map(str, row[:]) for row in csv_obj], dtype=str)
        pass

    def get_signal_by_name(self, signal_name):
        """
        This function returns the values of a signal given as input.
        When signal_name doesn't exist it returns 'None'

        :param signal_name:  the name of the signal
        :return: value of named signal or None
        """

        if isinstance(signal_name, str):
            if signal_name in self.__sigValDict:
                if self.__scan_opt != 'scan_force':
                    try:
                        return np.array(self.__sigValDict[signal_name], dtype=self.__sigTypDict[signal_name])
                    except ValueError:
                        return np.array(self.__sigValDict[signal_name], dtype=float)
                    except KeyError:
                        return np.array(self.__sigValDict[signal_name], dtype=float)
                else:
                    return np.array(self.__sigValDict[signal_name], dtype=self.__desired_type)
            elif signal_name in self.__file_header:
                tmp = "Signal '%s' is available, but  the values fot it are not yet retreived. " % (signal_name)
                tmp += "Call obj.read_signals_values('%s')" % (signal_name)
                warning(tmp)
                return None
            else:
                warning("Signal '%s' doesn't exist!" % signal_name)
                return None
        else:
            raise TypeError("Expected instance of type string, but found instance of '%s' and '%s'instead." %
                            type(signal_name) % type(signal_name))

        # Done
        return None

    def get_signal_index(self, signal_name):
        """
        This function returns the index of a signal given as input in the signal_name list.
        When signal_name doesn't exist  it returns 'None'

        :param signal_name:   the name of the signal
        :return: index of named signal or None
        """
        if isinstance(signal_name, str):
            if signal_name in self.__signal_names:
                return self.__signal_names.index(signal_name)
            else:
                warning("Signal '%s' doesn't exist!" % signal_name)
                return None
        else:
            raise TypeError("Expected instance of type string, but found instance of '%s' and '%s'instead." %
                            type(signal_name) % type(signal_name))

        return None

    def get_sig_names(self):
        return self.__signal_names

    def get_signal_by_index(self, index):
        """
        This function returns the Signal values for the requested signal index.
        When index exceeds the total number of signals, the method returns 'None'

        :param index:    the index for which we want the Signal values
        :return: value of indexed signal or None
        """
        list_signal_values = []
        if isinstance(index, int):
            if index <= len(self.__signal_names):
                signal_name = self.__signal_names[index]
                list_signal_values = self.__sigValDict[signal_name]
                try:
                    return np.array(list_signal_values, dtype=self.__sigTypDict[signal_name])
                except KeyError:
                    return np.array(list_signal_values, dtype=float)
            else:
                warning("Index %d doesn't exist!" % (index))
                return None
        else:
            raise TypeError("Expected instance of type int, but found instance of '%s' " % type(index))

        return None

    def get_file_header(self):
        """
        read csv file header if available
        :return: list of columns of csv file
        """
        if self.__file_path is None:
            return None

        csv_file = self.__open_file(self.__file_path)
        if csv_file is not None:
            csv_reader = reader(csv_file, delimiter=self.__delimiter)
            for i in range(self.__skip_lines):
                csv_reader.next()
            # get all signals name
            self.__file_header = csv_reader.next()
            if self.__file_header.count('') > 0:
                self.__file_header.remove('')
            for i in range(len(self.__file_header)):
                self.__file_header[i] = self.__file_header[i].lstrip()
            return self.__file_header
        else:
            csv_file.close()
            return None

"""
CHANGE LOG:
-----------
$Log: dlm.py  $
Revision 1.2 2016/03/31 16:36:27CEST Mertens, Sven (uidv7805) 
pylint fix
Revision 1.1 2015/04/23 19:04:30CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/io/project.pj
Revision 1.13 2014/11/06 14:10:31CET Mertens, Sven (uidv7805)
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:10:31 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.12 2014/09/09 10:28:55CEST Mertens, Sven (uidv7805)
adding deprecation in favor for SignalReader class, combining both
--- Added comments ---  uidv7805 [Sep 9, 2014 10:28:56 AM CEST]
Change Package : 260446:1 http://mks-psad:7002/im/viewissue?selection=260446
Revision 1.11 2013/05/15 18:23:24CEST Hospes, Gerd-Joachim (uidv8815)
extend signal dict clearing to other functions
--- Added comments ---  uidv8815 [May 15, 2013 6:23:24 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.10 2013/05/14 14:11:47CEST Hospes, Gerd-Joachim (uidv8815)
empty signal dict in case of errors as returned value is not used
--- Added comments ---  uidv8815 [May 14, 2013 2:11:47 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.9 2013/04/03 08:02:10CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:11 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/28 15:25:18CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:18 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/27 16:52:42CET Mertens, Sven (uidv7805)
pylint: another adaptation, resolving imports
Revision 1.6 2013/03/27 13:51:24CET Mertens, Sven (uidv7805)
pylint: bugfixing and error reduction
Revision 1.5 2013/03/22 08:24:23CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
Revision 1.4 2013/02/28 16:22:05CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguide.
--- Added comments ---  heckerr [Feb 28, 2013 4:22:05 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/28 08:12:09CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:09 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/27 16:19:51CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:52 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/26 17:11:08CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/io/project.pj
Revision 1.2 2013/02/26 14:36:44CET Hecker, Robert (heckerr)
Update Code partly regarding Pep8.
--- Added comments ---  heckerr [Feb 26, 2013 2:36:44 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/13 09:57:38CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/io/project.pj
Revision 1.13 2011/05/02 09:18:22CEST Dinu, Marius (DinuM)
Bugfix for signal type determination throughout the different possible values
(eg. first value-> long, second one ->float)
--- Added comments ---  DinuM [May 2, 2011 9:18:23 AM CEST]
Change Package : 41612:13 http://mks-psad:7002/im/viewissue?selection=41612
Revision 1.12 2011/02/01 09:37:02CET Marius Dinu (DinuM)
Bugfix in functions get_signal_by_name and get_signal_by_index to deal with
the case where every signal from the dlm file is empty
--- Added comments ---  DinuM [Feb 1, 2011 9:37:02 AM CET]
Change Package : 38195:12 http://mks-psad:7002/im/viewissue?selection=38195
Revision 1.11 2010/05/19 09:06:54CEST dkubera
remove logging
--- Added comments ---  dkubera [2010/05/19 07:06:54Z]
Change Package : 39727:3 http://LISS014:6001/im/viewissue?selection=39727
Revision 1.10 2010/02/19 14:11:03CET dkubera
minor docu fix
--- Added comments ---  dkubera [2010/02/19 13:11:03Z]
Change Package : 33974:2 http://LISS014:6001/im/viewissue?selection=33974
Revision 1.9 2009/11/23 18:28:13CET dkubera
- robustness of dirty input pathes (strip used)
- examples added to documentation
- documentation reworks (reST)
- type handling extended
--- Added comments ---  dkubera [2009/11/23 17:28:14Z]
Change Package : 33974:1 http://LISS014:6001/im/viewissue?selection=33974
Revision 1.8 2009/10/28 14:37:32CET dkubera
small memory bugfix
--- Added comments ---  dkubera [2009/10/28 13:37:32Z]
Change Package : 32862:1 http://LISS014:6001/im/viewissue?selection=32862
Revision 1.7 2009/10/16 12:12:31CEST Marius Dinu (mdinu)
Adapted class corresponding to Validation Framework needs:
 - default value for file path constructor parameter set to None
 - inserted public class method set_file_path()
 - changes in  get_file_header()  method according to modifications above.
--- Added comments ---  mdinu [2009/10/16 10:12:31Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
--- Added comments ---  mdinu [2009/10/16 10:12:31Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
Revision 1.6 2009/10/06 14:58:52EEST Marius Dinu (mdinu)
Removed prints for debugging purposes, fixed bug regarding method names
--- Added comments ---  mdinu [2009/10/06 11:58:53Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
--- Added comments ---  mdinu [2009/10/06 11:58:53Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
Revision 1.5 2009/10/02 09:36:18EEST Marius Dinu (mdinu)
Handling exception cases and changed method names according to stk_scripting_guidelines.doc. Added module header again
--- Added comments ---  mdinu [2009/10/02 06:36:19Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
--- Added comments ---  mdinu [2009/10/02 06:36:19Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
Revision 1.3 2009/09/30 19:40:50EEST dkubera
bugfix : call of stk_time instead of stk_time"r"
--- Added comments ---  dkubera [2009/09/30 16:40:50Z]
Change Package : 30703:1 http://LISS014:6001/im/viewissue?selection=30703
--- Added comments ---  dkubera [2009/09/30 16:40:50Z]
Change Package : 30703:1 http://LISS014:6001/im/viewissue?selection=30703
Revision 1.2 2009/09/23 14:44:21CEST Marius Dinu (mdinu)
Modified comment section in order to display MKS logging mechanism
--- Added comments ---  mdinu [2009/09/23 12:44:22Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
--- Added comments ---  mdinu [2009/09/23 12:44:22Z]
Change Package : 23922:1 http://LISS014:6001/im/viewissue?selection=23922
"""
