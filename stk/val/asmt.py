"""
stk/val/asmt.py
---------------

 Subpackage for Handling Assessment Class and States

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.5.1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/02/07 19:32:29CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import environ

# - import STK modules ------------------------------------------------------------------------------------------------
import stk.db.gbl.gbl as db_gbl
import stk.db.val.val as db_val
from stk.util.helper import deprecated, arg_trans
from stk.util.logger import Logger


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

    def load(self, dbi_gbl):
        """Load the assessment states

        :param dbi_gbl: global db interface
        :return: True on passed, False on Error
        """
        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._logger.error("GBL Database interface undefined")
            return False
        self.__type_id = dbi_gbl.get_val_observer_type_id(self.__type)
        self.__states = dbi_gbl.get_assessment_state(observer_type_id=self.__type_id)
        self.__default_stateid = dbi_gbl.get_assessment_state_id(self.NOT_ASSESSED)
        return True

    def save(self, dbi_gbl):
        """Save the assessment states

        :param dbi_gbl: GBL Database interface
        """
        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._logger.error("GBL Database interface undefined")
            return False

        self.__type_id = dbi_gbl.get_val_observer_type_id(self.__type)
        for state in self.__states:
            if db_gbl.COL_NAME_ASSESSMENT_STATE_ASSID not in state:
                state[db_gbl.COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID] = self.__type_id
                dbi_gbl.add_assessment_state(state)

        return True

    def add_state(self, name, desc):
        """ Get the Result Name

        :param name: name of assessment state
        :param desc: description of assessment state
        """
        for state in self.__states:
            if name.lower() == state[db_gbl.COL_NAME_ASSESSMENT_STATE_NAME]:
                return False
        self.__states.append({db_gbl.COL_NAME_ASSESSMENT_STATE_NAME: name,
                              db_gbl.COL_NAME_ASSESSMENT_STATE_DESCRIPTION: desc})
        return True

    @property
    def type(self):
        """ Get the Result Name
        """
        return self.__type

    def get_states(self, with_id=False):
        """ Return the list of assessment states or a key / value dictonary with ID and Name

        :param with_id:
        """
        if with_id is False:
            state_list = []
            for state in self.__states:
                state_list.append(state[db_gbl.COL_NAME_ASSESSMENT_STATE_NAME])

        else:
            state_list = {}
            for state in self.__states:
                state_list[state[db_gbl.COL_NAME_ASSESSMENT_STATE_ASSID]] = \
                    state[db_gbl.COL_NAME_ASSESSMENT_STATE_NAME]

        return state_list

    def get_state_id(self, state_name):
        """ Get State Identifier of the given Assessment

        :param state_name: Assessment State name
        """
        obs_typeids = [None]
        if self.__type_id is not None:
            obs_typeids.append(self.__type_id)
        for state in self.__states:
            if (state_name.lower() == state[db_gbl.COL_NAME_ASSESSMENT_STATE_NAME].lower() and
                    state[db_gbl.COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID] in obs_typeids):
                return state[db_gbl.COL_NAME_ASSESSMENT_STATE_ASSID]
        return self.__default_stateid

    def get_state_name(self, state_id):
        """ Get Assessment State by given Identifier

        :param state_id: Assessment State Identifier
        """
        for state in self.__states:
            if state_id == state[db_gbl.COL_NAME_ASSESSMENT_STATE_ASSID]:
                return state[db_gbl.COL_NAME_ASSESSMENT_STATE_NAME]

    @deprecated('load')
    def Load(self, dbi_gbl):  # pylint: disable=C0103
        """deprecated"""
        return self.load(dbi_gbl)

    @deprecated('save')
    def Save(self, dbi_gbl):  # pylint: disable=C0103
        """deprecated"""
        return self.save(dbi_gbl)

    @deprecated('add_state')
    def AddState(self, name, desc):  # pylint: disable=C0103
        """deprecated"""
        return self.add_state(name, desc)

    @deprecated('type (property)')
    def GetType(self):  # pylint: disable=C0103
        """deprecated"""
        return self.type

    @deprecated('get_states')
    def GetStates(self, with_id=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_states(with_id)

    @deprecated('get_state_id')
    def GetStateId(self, state_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_id(state_name)

    @deprecated('get_state_name')
    def GetStateName(self, state_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_name(state_id)


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

    def load(self, dbi_gbl):
        """ Load the assessment states

        :param dbi_gbl: global db interface
        :return: True on passed, False on Error
        """
        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._logger.error("GBL Database interface undefined")
            return False

        for wf_name in self.__workflow_list:
            wflow = dbi_gbl.get_workflow(wf_name)
            if db_gbl.COL_NAME_WORKFLOW_WFID in wflow:
                self.__workflows.append(wflow)
        return True

    def get_states(self):
        """ Return the list of workflow states
        """
        state_list = []
        for state in self.__workflows:
            state.append(state[db_gbl.COL_NAME_WORKFLOW_NAME])

        return state_list

    def get_state_id(self, wf_name):
        """ Get Workflow State

        :param wf_name: name of workflow
        """
        for state in self.__workflows:
            if wf_name.lower() == state[db_gbl.COL_NAME_WORKFLOW_NAME].lower():
                return state[db_gbl.COL_NAME_WORKFLOW_WFID]

        return None

    def get_state_name(self, wf_id):
        """ Get Workflow State

        :param wf_id: id of workflow
        """
        for state in self.__workflows:
            if wf_id == state[db_gbl.COL_NAME_WORKFLOW_WFID]:
                return state[db_gbl.COL_NAME_WORKFLOW_NAME]

        return None

    @deprecated('load')
    def Load(self, dbi_gbl):  # pylint: disable=C0103
        """deprecated"""
        return self.load(dbi_gbl)

    @deprecated('get_states')
    def GetStates(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_states()

    @deprecated('get_state_id')
    def GetStateId(self, wf_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_id(wf_name)

    @deprecated('get_state_name')
    def GetStateName(self, wf_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_state_name(wf_id)


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

    def load(self, ass_id, dbi_val, dbi_gbl, val_obs_name):
        """ The Assessment from DB

        :param ass_id: Assessment ID
        :param dbi_val: VAL Database interface
        :param dbi_gbl:  GBL Database interface
        :param val_obs_name: name of observer
        """
        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._logger.error("VAL Database interface undefined")
            return False

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._logger.error("GBL Database interface undefined")
            return False

        self.__load_states(dbi_gbl, val_obs_name)

        entries = dbi_val.get_assessment(ass_id)
        if len(entries) == 0:
            self._logger.error("No result for Assessment ID was not found")
            return False
        elif len(entries) == 1:
            record = entries[0]
            self.__id = record[db_val.COL_NAME_ASS_ID]
            self.__user_id = record[db_val.COL_NAME_ASS_USER_ID]
            self.__ass_comment = record[db_val.COL_NAME_ASS_COMMENT]
            self.__date_time = record[db_val.COL_NAME_ASS_DATE]
            self.__issue = record[db_val.COL_NAME_ASS_TRACKING_ID]
            wf_id = record[db_val.COL_NAME_ASS_WFID]
            self.__wf_state = self.__ass_wf.get_state_name(wf_id)

            self.__user_account = dbi_gbl.get_user(user_id=self.__user_id)[db_gbl.COL_NAME_USER_LOGIN]

            assst_id = record[db_val.COL_NAME_ASS_ASSSTID]
            self.__ass_state = self.__ass_states.get_state_name(assst_id)
            return True

        return False

    def save(self, dbi_val, dbi_gbl, val_obs_name):
        """ Save the result

        :type dbi_val: validation DB connection
        :param dbi_gbl: global DB connection
        :param val_obs_name: name of observer
        """
        record = {}
        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._logger.error("VAL Database interface undefined")
            return False

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._logger.error("GBL Database interface undefined")
            return False

        self.__load_states(dbi_gbl, val_obs_name)
        if self.__user_id is None:
            self.__user_id = dbi_gbl.current_gbluserid

        record[db_val.COL_NAME_ASS_USER_ID] = self.__user_id
        record[db_val.COL_NAME_ASS_COMMENT] = self.__ass_comment
        record[db_val.COL_NAME_ASS_TRACKING_ID] = self.__issue
        wf_id = self.__ass_wf.get_state_id(self.__wf_state)
        record[db_val.COL_NAME_ASS_WFID] = wf_id

        record[db_val.COL_NAME_ASS_DATE] = self.__date_time
        assst_id = self.__ass_states.get_state_id(self.__ass_state)
        record[db_val.COL_NAME_ASS_ASSSTID] = assst_id

        self.__id = dbi_val.add_assessment(record)
        # by default db sets current db date to assessment date entries if nothing is passed
        # so setting it for further work with the assessment (e.g. in report) has to be done after adding
        # because the db returns date time in different format as it expects for setting
        if self.__date_time is None:
            self.__date_time = dbi_gbl.curr_date_time()

        return True

    def update(self, dbi_val, dbi_gbl, val_obs_name):
        """ Update the Assessment

        :param dbi_val: validation db connection
        :param dbi_gbl: global db connection
        :type val_obs_name: observer name
        """
        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._logger.error("VAL Database interface undefined")
            return False

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._logger.error("GBL Database interface undefined")
            return False
        if self.__id is None:
            self._logger.error("Cannot Update Unsaved/Unloaded Assessment")
            return False
        else:
            if dbi_val.is_assessment_locked(self.__id):
                self._logger.error("Cannot Update Assessment due to Locked Testrun")
                return False
            record = {}
            self.__load_states(dbi_gbl, val_obs_name)
            user = dbi_gbl.get_user(login=environ["USERNAME"])
            self.__user_id = user[db_gbl.COL_NAME_USER_ID]
            record[db_val.COL_NAME_ASS_ID] = self.__id
            record[db_val.COL_NAME_ASS_USER_ID] = self.__user_id
            record[db_val.COL_NAME_ASS_COMMENT] = self.__ass_comment
            record[db_val.COL_NAME_ASS_TRACKING_ID] = self.__issue
            assst_id = self.__ass_states.get_state_id(self.__ass_state)
            record[db_val.COL_NAME_ASS_ASSSTID] = assst_id
            self.__date_time = dbi_gbl.curr_date_time()

            record[db_val.COL_NAME_ASS_DATE] = self.__date_time
            wf_id = self.__ass_wf.get_state_id(ValAssessmentWorkFlows.ASS_WF_MANUAL)
            record[db_val.COL_NAME_ASS_WFID] = wf_id
            dbi_val.update_assessment(record)
            self.load(self.__id, dbi_val, dbi_gbl, val_obs_name)

    def __load_states(self, dbi_gbl, val_obs_name):
        """ Load the States """

        if self.__ass_states is None:
            self.__ass_states = ValAssessmentStates(val_obs_name)
            self.__ass_states.load(dbi_gbl)

        if self.__ass_wf is None:
            self.__ass_wf = ValAssessmentWorkFlows()
            self.__ass_wf.load(dbi_gbl)

    @property
    def user_id(self):
        """ Get the User Name
        """
        return self.__user_id

    @property
    def user_account(self):
        """ return the account name of the user
        """
        return self.__user_account

    @property
    def ass_id(self):
        """Get the Assessment Identifier
        """
        return self.__id

    @ass_id.setter
    def ass_id(self, value):
        """setter property for Assessment ID

        :param value: id of assessment
        """
        self.__id = value

    @property
    def wf_state(self):
        """Get the Assessment WorkFlow State
        """
        return self.__wf_state

    def __get_wf_state(self):
        """
        getter for workflow state
        """
        return self.__wf_state

    def __set_wf_state(self, value):
        """
        setter property for workflow state
        """
        self.__wf_state = value

    wf_state = property(__get_wf_state, __set_wf_state)

    @property
    def comment(self):
        """ getter for property `comment` """
        return self.__ass_comment

    @comment.setter
    def comment(self, value):
        """ setter for property `comment`

        :param value: comment of assessment
        """
        self.__ass_comment = value

    @property
    def ass_state(self):
        """ getter for property `comment` """
        return self.__ass_state

    @ass_state.setter
    def ass_state(self, value):
        """ setter for property `comment`

        :param value: state of assessment
        """
        self.__ass_state = value

    @property
    def issue(self):
        """ getter for property `comment` """
        return self.__issue

    @issue.setter
    def issue(self, value):
        """ setter for property `comment`

        :param value: MKS issue of assessment
        """
        self.__issue = value

    @property
    def date(self):
        """ Get Assessment Date when last time it was inserted/modified
        """
        return self.__date_time

    @deprecated('date (property)')
    def GetDate(self):  # pylint: disable=C0103
        """deprecated"""
        return self.date

    @deprecated('load')
    def Load(self, ass_id, dbi_val, dbi_gbl, val_obs_name):  # pylint: disable=C0103
        """deprecated"""
        return self.load(ass_id, dbi_val, dbi_gbl, val_obs_name)

    @deprecated('save')
    def Save(self, dbi_val, dbi_gbl, val_obs_name):  # pylint: disable=C0103
        """deprecated"""
        return self.save(dbi_val, dbi_gbl, val_obs_name)

    @deprecated('update')
    def Update(self, dbi_val, dbi_gbl, val_obs_name):  # pylint: disable=C0103
        """deprecated"""
        return self.update(dbi_val, dbi_gbl, val_obs_name)

    @deprecated('user_id (property)')
    def GetUserId(self):  # pylint: disable=C0103
        """deprecated"""
        return self.user_id

    @deprecated('user_account (property)')
    def GetUserAccount(self):  # pylint: disable=C0103
        """deprecated"""
        return self.user_account

    @deprecated('ass_id (property)')
    def GetId(self):  # pylint: disable=C0103
        """deprecated"""
        return self.ass_id

    @deprecated('comment (property)')
    def GetComment(self):  # pylint: disable=C0103
        """deprecated"""
        return self.comment

    @deprecated('comment (property)')
    def SetComment(self, comment):  # pylint: disable=C0103
        """deprecated"""
        self.comment = comment

    @deprecated('ass_state (property)')
    def GetAssesmentState(self):  # pylint: disable=C0103
        """deprecated"""
        return self.ass_state

    @deprecated('ass_state (property)')
    def SetAssesmentState(self, ass_state):  # pylint: disable=C0103
        """deprecated"""
        self.ass_state = ass_state

    @deprecated('issue (property)')
    def GetIssue(self):  # pylint: disable=C0103
        """deprecated"""
        return self.issue

    @deprecated('issue (property)')
    def SetIssue(self, issue):  # pylint: disable=C0103
        """deprecated"""
        self.issue = issue


"""
CHANGE LOG:
-----------
$Log: asmt.py  $
Revision 1.5.1.1 2017/02/07 19:32:29CET Hospes, Gerd-Joachim (uidv8815) 
change size of result description and name, adappt test to check on Oracle,
fix date setting, still problem: Oracle returned date can not be used as input for date
Revision 1.5 2015/12/07 10:35:48CET Mertens, Sven (uidv7805)
some pep8 / lint fixes
Revision 1.4 2015/10/05 12:53:39CEST Ahmed, Zaheer (uidu7634)
prevent update assessment for a locked testrun
- Added comments -  uidu7634 [Oct 5, 2015 12:53:40 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.3 2015/07/14 08:30:11CEST Mertens, Sven (uidv7805)
curr_date_time is from base class
--- Added comments ---  uidv7805 [Jul 14, 2015 8:30:12 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/05/05 14:40:09CEST Ahmed, Zaheer (uidu7634)
grab primary key directly from db interface propery no query
--- Added comments ---  uidu7634 [May 5, 2015 2:40:10 PM CEST]
Change Package : 318797:5 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.1 2015/04/23 19:05:36CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/val/project.pj
Revision 1.24 2015/03/12 10:52:48CET Ahmed, Zaheer (uidu7634)
bug fix to return correct state id which is related to observertypeid
otherwise return default assessment stateid of Not Assessed
--- Added comments ---  uidu7634 [Mar 12, 2015 10:52:49 AM CET]
Change Package : 315256:1 http://mks-psad:7002/im/viewissue?selection=315256
Revision 1.23 2015/03/11 16:14:18CET Ahmed, Zaheer (uidu7634)
reload assessment states on update
--- Added comments ---  uidu7634 [Mar 11, 2015 4:14:18 PM CET]
Change Package : 315256:1 http://mks-psad:7002/im/viewissue?selection=315256
Revision 1.22 2015/03/06 14:55:06CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Mar 6, 2015 2:55:07 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.21 2015/03/06 14:23:16CET Mertens, Sven (uidv7805)
changing logger
--- Added comments ---  uidv7805 [Mar 6, 2015 2:23:17 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.20 2015/02/26 16:30:04CET Ahmed, Zaheer (uidu7634)
added property function to get workflow state for asessement
--- Added comments ---  uidu7634 [Feb 26, 2015 4:30:05 PM CET]
Change Package : 310109:1 http://mks-psad:7002/im/viewissue?selection=310109
Revision 1.19 2015/01/19 16:25:41CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 19, 2015 4:25:42 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.18 2014/12/17 14:57:45CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 2:57:45 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.17 2014/11/07 11:00:00CET Mertens, Sven (uidv7805)
fixing deprecation messages by using new replacements
--- Added comments ---  uidv7805 [Nov 7, 2014 11:00:01 AM CET]
Change Package : 278242:1 http://mks-psad:7002/im/viewissue?selection=278242
Revision 1.16 2014/10/22 11:46:20CEST Ahmed, Zaheer (uidu7634)
Removed deprecated method usage
--- Added comments ---  uidu7634 [Oct 22, 2014 11:46:21 AM CEST]
Change Package : 267593:5 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.15 2014/10/14 14:45:38CEST Ahmed, Zaheer (uidu7634)
Add get set property function for Assessment Id
--- Added comments ---  uidu7634 [Oct 14, 2014 2:45:39 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.14 2014/09/17 13:12:37CEST Hecker, Robert (heckerr)
Fixed some issued.
--- Added comments ---  heckerr [Sep 17, 2014 1:12:38 PM CEST]
Change Package : 264782:1 http://mks-psad:7002/im/viewissue?selection=264782
Revision 1.13 2014/09/17 11:50:38CEST Hecker, Robert (heckerr)
Moved to new coding guidelines with keeping old Methods.
--- Added comments ---  heckerr [Sep 17, 2014 11:50:38 AM CEST]
Change Package : 264782:1 http://mks-psad:7002/im/viewissue?selection=264782
Revision 1.12 2014/02/20 12:57:00CET Hospes, Gerd-Joachim (uidv8815)
print user accunt instead of db internal userid
--- Added comments ---  uidv8815 [Feb 20, 2014 12:57:01 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
"""
