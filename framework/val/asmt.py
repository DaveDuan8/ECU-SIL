"""
framework/val/asmt.py
---------------

 Subpackage for Handling Assessment Class and States

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:23:59CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------

# - import framework modules ------------------------------------------------------------------------------------------------
from framework.util.helper import arg_trans
from framework.util.logger import Logger


# - classes -----------------------------------------------------------------------------------------------------------
class ValAssessmentStates(object):
    """ Base class for assessments states
    """
    PASSED = "Passed"
    FAILED = "Failed"
    INVESTIGATE = "Investigate"
    NOT_ASSESSED = "Not Assessed"

    def __init__(self, obs_type):
        """Constructor for Assessment class

        :param obs_type: Name of the observer type
        """
        self.__states = []
        self.__type = obs_type
        self.__type_id = None
        self._logger = Logger(self.__class__.__name__)
        self.__default_stateid = None


class ValAssessmentWorkFlows(object):
    """ Base class for assessments workflows
    """
    ASS_WF_AUTO = "automatic"
    ASS_WF_MANUAL = "manual"
    ASS_WF_REVIEWED = "verified"
    ASS_WF_REJECTED = "rejected"

    def __init__(self):
        """ Initialize the workflow class
        """
        #  List of Workflow States
        self.__workflows = []
        self.__workflow_list = [ValAssessmentWorkFlows.ASS_WF_AUTO,
                                ValAssessmentWorkFlows.ASS_WF_MANUAL,
                                ValAssessmentWorkFlows.ASS_WF_REVIEWED,
                                ValAssessmentWorkFlows.ASS_WF_REJECTED]
        #  Observer Type
        self.__type = type
        self._logger = Logger(self.__class__.__name__)


class ValAssessment(object):
    """ Base class for assessments
    """
    def __init__(self, *args, **kwargs):
        """(init)

        :keyword user_id: User Id
        :keyword wf_state: Workflow State
        :keyword ass_state: Assessment State
        :keyword ass_comment: Assessment Comment
        :keyword issue: Issue name from MKS
        """
        opts = arg_trans(['user_id', 'wf_state', 'ass_state', 'ass_comment', 'date_time', 'issue'], *args, **kwargs)
        self.__user_id = opts[0]
        self.__wf_state = opts[1]
        self.__ass_state = opts[2]
        self.__ass_comment = opts[3]
        self.__date_time = opts[4]
        self.__issue = opts[5]
        self.__id = None
        self.__ass_states = None
        self.__ass_wf = None
        self.__user_account = None
        self._logger = Logger(self.__class__.__name__)

    def __str__(self):
        """ Return the Assessment as String
        """
        txt = "ValAssessment:\n"
        if self.__id is not None:
            txt += str(" ID: %s" % self.__id)
        else:
            txt += str(" ID: -")

        txt += str(" Status: '%s'" % self.__wf_state)
        txt += str(" Result: '%s'" % self.__ass_state)
        if self.__issue is not None:
            txt += str(" Issue: %s" % self.__issue)

        txt += str(" Date: %s" % self.__date_time)
        txt += str(" Info: '%s'" % self.__ass_comment)
        return txt

    @property
    def user_id(self):
        """ Get the User Name
        """
        return self.__user_id

    @property
    def ass_state(self):
        """ getter for property `comment` """
        return self.__ass_state

    @property
    def issue(self):
        """ getter for property `comment` """
        return self.__issue

    @property
    def date(self):
        """ Get Assessment Date when last time it was inserted/modified
        """
        return self.__date_time

"""
CHANGE LOG:
-----------
$Log: asmt.py  $
Revision 1.2 2020/03/31 09:23:59CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:34:05CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
