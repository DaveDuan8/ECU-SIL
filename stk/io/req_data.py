"""
req_data.py
-------------------------

Class for storing and persisting requirements data.

:org:           Continental AG
:author:        Christoph Castell

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:30CEST $
"""
# Import Python Modules -------------------------------------------------------
from copy import deepcopy
from xml.dom.minidom import parse, Document

# Import STK Modules ----------------------------------------------------------

# Defines ---------------------------------------------------------------------
REQ_ID = "doors_id"  # The requirement id from DOORS.
REQ_NAME = "name"  # The name from DOORS or free text.
REQ_DESC = "description"  # The description from DOORS or free text.
REQ_VAL_NATURE = "value_nature"  # [average, min, max]
REQ_VAL_SCOPE = "value_scope"  # [event, file, collection]
REQ_VAL_UNITS = "value_units"  # [m, km, us, ms, s, m/s, m/s^2, km/h, deg, rad, %]
REQ_COMPARITOR = "comparitor"  # [<, >, <=, >=, ==]
REQ_PARAMETER = "parameter"  # The doors_id of the relevant parameter.
REQ_TEST = "test"  # [true, false] Is the parameter being requiremented.

REQ_PAR_ID = "doors_id"  # The parameter id from DOORS.
REQ_PAR_NAME = "name"  # The name from DOORS or free text.
REQ_PAR_DESC = "description"  # The description from DOORS or free text.
REQ_PAR_NATURE = "nature"  # [value, linear_function]
REQ_PAR_VAL1 = "value1"  # Comparison value or 'a' for linear function.
REQ_PAR_VAL2 = "value2"  # Nothing or 'b' for linear function.
REQ_PAR_VAL3 = "value3"  # optional values
REQ_PAR_VAL4 = "value4"  # optional values
REQ_PAR_UNITS = "units"  # [m, km, micro_s, milli_s, s, m/s, m/s^2, km/h, deg, rad]

REQ_COMP_LT = "<"
REQ_COMP_GT = ">"
REQ_COMP_LE = "<="
REQ_COMP_GE = ">="
REQ_COMP_EQ = "&eq;"

# Functions -------------------------------------------------------------------

# Classes ---------------------------------------------------------------------


class RequirementsData(object):
    """ Manages requirements data. """
    def __init__(self):
        """ Class initialisation. """

        # Initialize Variables.
        self.__dom = None
        self.__dom_file_path = ""

        # The field data that a parameter contains.
        self.req_field_data = [REQ_ID,
                               REQ_NAME,
                               REQ_DESC,
                               REQ_VAL_NATURE,
                               REQ_VAL_SCOPE,
                               REQ_VAL_UNITS,
                               REQ_COMPARITOR,
                               REQ_PARAMETER,
                               REQ_TEST]  # [true, false] Is the parameter being requiremented.

        self.param_field_data = [REQ_PAR_ID, REQ_PAR_NAME, REQ_PAR_DESC,
                                 REQ_PAR_NATURE, REQ_PAR_VAL1, REQ_PAR_VAL2,
                                 REQ_PAR_VAL3, REQ_PAR_VAL4, REQ_PAR_UNITS]

        # The parameter set in the form of a table.
        self.req_table_data = []
        self.req_num_columns = 0
        self.req_num_rows = 0

        self.param_table_data = []
        self.param_num_columns = 0
        self.param_num_rows = 0

    def Read(self, req_file_path):
        """ Read in the requirements file.
        @param req_file_path: The path to the requirements xml file.
        """
        self.__dom_file_path = req_file_path
        self.__dom = parse(self.__dom_file_path)

        # Extract the data for the parameter table.
        self.UpdateTableDataFromDom()

    def UpdateTableDataFromDom(self):
        """ Update the table data structure from the dom data structure. """
        # Parameters
        self.param_table_data = []
        parameters = self.__dom.getElementsByTagName('parameter')

        for param in parameters:
            param_data = []
            for item in self.param_field_data:
                param_data.append(param.getAttribute(item))
            self.param_table_data.append(deepcopy(param_data))

        self.param_num_columns = len(self.param_field_data)
        self.param_num_rows = len(parameters)

        # Requirements.
        self.req_table_data = []
        requirements = self.__dom.getElementsByTagName('requirement')

        for req in requirements:
            req_data = []
            for item in self.req_field_data:
                req_data.append(req.getAttribute(item))
            self.req_table_data.append(deepcopy(req_data))

        self.req_num_columns = len(self.req_field_data)
        self.req_num_rows = len(requirements)

    def SetModule(self, req_file_path):
        """ Read in the new module.
        @param req_module_name: The name of the requirements module.
        """
        self.Read(req_file_path)

    def GetParameters(self):
        """ Get a list of parameters from the requirements file.
        @return: List of parameters.
        """
        return self.__dom.getElementsByTagName("parameter")

    def GetParameterIds(self):
        """ Get a list of parameter ids from the requirements file.
        @return: List of parameter ids.
        """
        parameter_ids = []
        parameters = self.GetParameters()
        for parameter in parameters:
            parameter_ids.append(parameter.getAttribute("doors_id"))
        return parameter_ids

    def GetParameter(self, doors_id):
        """ Get a specific parameter from the requirements file.
        @param doors_id: Parameter identifier from DOORS.
        @return: Parameter or None.
        """
        parameters = self.GetParameters()
        for parameter in parameters:
            if doors_id == parameter.getAttribute("doors_id"):
                return parameter
        return None

    def GetParameterData(self, doors_id, field_list):
        """ Get parameter data from the requirements file.
        @param doors_id: Parameter identifier from DOORS.
        @param field_list: The list of data to be extracted from the parameter.
        @return: List of data for the specified parameter.
        """
        param_data = []
        param = self.GetParameter(doors_id)
        for item in field_list:
            param_data.append(param.getAttribute(item))
        return param_data

    def GetSingleParameterData(self, doors_id, field):
        """ Get parameter data from the requirements file.
        @param doors_id: Parameter identifier from DOORS.
        @param field: The data to be extracted from the parameter.
        @return: data for the specified parameter.
        """
#        param_data = []
        param = self.GetParameter(doors_id)
        if param:
            return param.getAttribute(field)
        else:
            return None

    def CreateParameter(self, param_data):
        """ Create a new parameter from the given data.
        @param param_data: A list of data to construct the requirement parameter.
        @return: parameter
        """
        param = self.__dom.createElement("parameter")
        for data in param_data:
            param.setAttributeNode(self.__dom.createAttribute(data))
        return param

    def AppendParameter(self, new_param):
        """ Append the given parameter to the dom.
        @param new_param: Parameter to append.
        """
        parameters_element = self.__dom.getElementsByTagName("parameters")
        parameters_element.appendChild(new_param)

    def DeleteParameter(self, param_id):
        """ Delete the given parameter from the dom.
        @param param_id: Parameter identifier from DOORS.
        """
        pass

    def GetRequirements(self):
        """ Get a list of requirements from the requirements file.
        @return: List of requirements.
        """
        return self.__dom.getElementsByTagName("requirement")

    def GetRequirementIds(self):
        """ Get a list of requirement ids from the requirements file.
        @return: List of requirement ids.
        """
        requirement_ids = []
        requirements = self.GetRequirements()
        for requirement in requirements:
            requirement_ids.append(requirement.getAttribute("doors_id"))
        return requirement_ids

    def GetRequirement(self, doors_id):
        """ Get a specific requirement from the requirements file.
        @param doors_id: Requirement identifier from DOORS.
        @return: Requirement or None.
        """
        requirements = self.GetRequirements()
        for requirement in requirements:
            if doors_id == requirement.getAttribute("doors_id"):
                return requirement
        return None

    def GetRequirementData(self, doors_id, field_list=None):
        """ Get requirement data from requirement.
        @param doors_id: Requirement identifier from DOORS.
        @param field_list: The list of data to be extracted from the requirement.
        @return: List of data for requirement.
        """
        param = self.GetRequirement(doors_id)

        if field_list is None:
            param_data = {}
            for idx in range(param.attributes.length):
                attr = param.attributes.item(idx)
                param_data[attr.name] = attr.value
        else:
            param_data = []
            for item in field_list:
                param_data.append(param.getAttribute(item))

        return param_data

    def CreateRequirement(self, param_data):
        """ Create a new requirement from the given data.
        @param param_data: A list of data to construct the requirement requirement.
        @return: requirement
        """
        param = self.__dom.createElement("requirement")
        for data in param_data:
            param.setAttributeNode(self.__dom.createAttribute(data))
        return param

    def AppendRequirement(self, new_param):
        """ Append the given requirement to the dom.
        @param new_param: Requirement to append.
        """
        requirements_element = self.__dom.getElementsByTagName("requirements")
        requirements_element.appendChild(new_param)

    def DeleteRequirement(self, param_id):
        """ Delete the given requirement from the dom.
        @param param_id: Requirement identifier from DOORS.
        """
        pass

    def Write(self, req_file_path=None):
        """ Write out the requirements file.
        @param req_file_path: The path to the requirements xml file.
        """
        if req_file_path is None:
            req_file_path = self.__dom_file_path

        xml = Document()

        # Creates user element
        root = xml.createElement("BatchList")
        # Append Root Element
        xml.appendChild(root)

        for i in range(0, len(self.__RecFileList)):

            el = xml.createElement('BatchEntry')
            el.setAttribute("fileName", self.__RecFileList[i])
            root.appendChild(el)

        fp = open(req_file_path, "w")
        xml.writexml(fp, addindent="    ", newl="\n", encoding="UTF-8")
        fp.close()

"""
CHANGE LOG:
-----------
$Log: req_data.py  $
Revision 1.1 2015/04/23 19:04:30CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/io/project.pj
Revision 1.7 2014/11/06 14:10:32CET Mertens, Sven (uidv7805) 
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:10:32 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.6 2013/03/27 13:51:27CET Mertens, Sven (uidv7805)
pylint: bugfixing and error reduction
--- Added comments ---  uidv7805 [Mar 27, 2013 1:51:28 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/01 16:37:21CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguide.
--- Added comments ---  heckerr [Mar 1, 2013 4:37:21 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/28 08:12:28CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:28 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 16:20:01CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:20:01 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/26 20:13:11CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:13:12 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 10:32:44CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/io/project.pj
Revision 1.8 2012/11/05 14:00:24CET Hammernik-EXT, Dmitri (uidu5219)
- changed GetRequirementData, added additional parameter to get
requirements data as a dictionary
--- Added comments ---  uidu5219 [Nov 5, 2012 2:00:26 PM CET]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.7 2012/04/24 17:10:42CEST Raedler-EXT, Guenther (uidt9430)
- added new function to retrieve a single parameter
- added global define of xml attributes
--- Added comments ---  uidt9430 [Apr 24, 2012 5:10:45 PM CEST]
Change Package : 100282:1 http://mks-psad:7002/im/viewissue?selection=100282
Revision 1.6 2012/02/14 12:37:10CET Raedler-EXT, Guenther (uidt9430)
- support 4 parameters for requirements
--- Added comments ---  uidt9430 [Feb 14, 2012 12:37:10 PM CET]
Change Package : 90579:2 http://mks-psad:7002/im/viewissue?selection=90579
Revision 1.5 2011/09/22 13:32:49CEST Castell Christoph (uidt6394) (uidt6394)
Minor change to xml file write.
--- Added comments ---  uidt6394 [Sep 22, 2011 1:32:49 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.4 2011/07/15 09:27:28CEST Castell Christoph (uidt6394) (uidt6394)
GetParameterData bug fix.
--- Added comments ---  uidt6394 [Jul 15, 2011 9:27:28 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.3 2011/07/15 08:57:21CEST Castell Christoph (uidt6394) (uidt6394)
Fixed GetParameter, GetParameterData, GetRequirement and GetRequirementData.
--- Added comments ---  uidt6394 [Jul 15, 2011 8:57:22 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/07/05 10:42:23CEST Castell Christoph (uidt6394) (uidt6394)
Fixed unit descriptions.
--- Added comments ---  uidt6394 [Jul 5, 2011 10:42:23 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.1 2011/07/04 10:18:08CEST Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/
05_Testing/05_Test_Environment/algo/ars301_req_test/valf_tests/vpc/project.pj
"""
