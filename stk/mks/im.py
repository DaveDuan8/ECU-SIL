"""
stk/mks/im
----------

Module IM (Integrity Management) provides a Interface to the
Integrity Manager client of MKS.

:org:           Continental AG
:author:        Robert Hecker

:creation date: 26.04.2014

:version:       $Revision: 1.8 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/03/15 19:32:36CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
import subprocess

# - defines -----------------------------------------------------------------------------------------------------------
DEBUG = 0


# - functions ---------------------------------------------------------------------------------------------------------
def get_release_item(release_id):
    """
    Read out a complete Release Issue from MKS with all the dependend
    CR's, FR's and Tasks.

    :param release_id:
    :type release_id:
    :return: Whole MKS Release Item
    :rtype: Object of Type `MksRelease`
    """
    imgr = Im()
    # Get the Release Information
    rel_issue = imgr.viewissue(release_id)
    if type(rel_issue) == ImsIssue:
        if not rel_issue['type'] and rel_issue['type'] == 'Release':
            raise LookupError("issue %s is not of type AD_Release!" % release_id)

        # Go through all Issues and Append them
        # planned items contains ROs (from issues or directly ordered) in this release:
        sub_issues = []
        for item in rel_issue['planned_items']:
            sub_issues.append(imgr.viewissue(item))
        rel_issue['planned_items_entries'] = sub_issues
        # planned requests list issues requested for this release:
        sub_issues = []
        for item in rel_issue['planned_requests']:
            sub_issues.append(imgr.viewissue(item))
        rel_issue['planned_requests_entries'] = sub_issues

    else:  # old mks AD_Release
        raise LookupError("issue {} is not of type Release!".format(release_id))

    return rel_issue


def get_issue(issue_id):
    """
    return issue with all fields as dict

    :param issue_id: IMS issue id
    :type  issue_id: int
    :return: ImsIssue
    """
    im = Im()
    issue = im.viewissue(issue_id)

    return issue


def edit_issue(issue_id, **fields):
    """
    change issue values of given issue

    :param issue_id: IMS id of issue to change
    :type  issue_id: int
    :param fields: additional arguments to pass to the edit command, keywords need to be valid parameters of the issue
    :return: result (error state) of the im commend
    """
    im = Im()
    ret = im.editissue(issue_id, fields)

    return ret


# Classes ----------------------------------------------------------------------
class ImsIssue(dict):
    """
    Data Container for all data which belongs to an IMS Issue,
    this could be some original issue, a release, a realisation order or others

    Special lists define if the entry is a string, list or multi line string.

    :author: Joachim Hospes
    :date:   27.02.2015
    """
    STRINGS = []  # everything that's not in the other lists
    MULTI_LINES = [  # in issue:
                     'description', 'members_of_field_decision_team', 'ccb_comment',
                     'comment', 'analysis_summary',
                     'comment_by_collaboration_partner', 'comment_to_collaboration_partner', 'proposed_solution',
                     'attachments', 'forward_relationships', 'backward_relationships',
                     # in RO:
                     'cancel_reason',
                     # in release:
                     'obsolete_reason']
    # fields following the multi line output of issues, used to mark end of field:
    END_MARKS = [  # in issue:
                   "released_checkpoint", "ccb_comment", "members_of_field_decision_team", "cancel_reason"
                   "total_realization_effort_estimated_by_analysis_[h]", "functional_variant",
                   "comment_to_collaboration_partner", "requested_feedback", "attachments",
                   "forward_relationships", "backward_relationships",
                   # in RO:
                   "cancel_reason", "planned_release",
                   # in release:
                   'links_to_source',
                   'comment_to_collaboration_partner', 'requesting_feedback', 'total_estimated_effort[h]',
                   'actual_release_date', 'total_realization_effort[h]', 'forward_relationships']
    # Id lists that should be parsed also, others are just listed as comma separated values in a string
    ID_LISTS = [  # in issue:
                  'sub_issues', 'analysis_tasks', 'orders', 'concerns', 'is_related_to', 'transfer_definitions',
                  # in release
                  'child_releases', 'planned_items', 'planned_requests']


class ImException(Exception):
    """
    Im Exception class which prints the Error Code and the message
    from the cli call.

    :author:        Robert Hecker
    :date:          26.04.2013
    """

    def __init__(self, error, message):
        Exception.__init__(self)
        self.error = error
        self.message = message

    def __str__(self):
        return "ErrorCode %d \n %s" % (self.error, self.message)


class ImParser(object):
    def __init__(self):
        """
        Init method of the ImParser Object.
        """
        pass

    @staticmethod
    def __parse_ims_multiline(idx, issue_desc):
        """
        parse multi line fields of IMS entries to get the end of the field (next entry) and concatenated context

        :param idx: start line index
        :type idx:  integer
        :param issue_desc: list of lines taken from im output
        :type issue_desc:  list[string]
        :return: updated index, concatenated lines
        :rtype: tuple(integer, string)
        """
        line = issue_desc[idx]
        mylist = line.split(":", 1)
        description = mylist[1]
        idx += 1

        while idx < len(issue_desc) \
                and issue_desc[idx].split(":", 1)[0].lower().replace(" ", "_") not in ImsIssue.END_MARKS:
            # Get next Line
            line = issue_desc[idx]
            description += '\n' + line
            idx += 1

        return idx - 1, description

    def __create_ims_entry(self, issue_desc):
        """
        convert a list of issue strings to an IMS entry Object.

        :param issue_desc: return of im viewissue
        :type issue_desc: list[string]

        :return: IMS issue content as dict.
        :rtype:  ImsIssue
        """
        ims_data = ImsIssue()
        idx = 0

        while idx < len(issue_desc):

            # Get actual Issue line
            line = issue_desc[idx]
            mylist = line.split(":", 1)

            if mylist[0] != '':
                keywrd = mylist[0].lower().replace(' ', '_')
                if keywrd in ImsIssue.MULTI_LINES:
                    ims_data.type = mylist[1].strip()
                    idx, ims_data[keywrd] = self.__parse_ims_multiline(idx, issue_desc)
                elif keywrd in ImsIssue.ID_LISTS:
                    if mylist[1]:
                        ims_data[keywrd] = [i.strip() for i in mylist[1].split(',') if len(i) > 1]
                elif keywrd:
                    try:
                        ims_data[keywrd] = mylist[1].strip()
                    except:
                        pass

            idx += 1

        return ims_data

    def convert(self, issue_desc):
        """
        convert a list of issue strings to a MKS Data Structure.

        :param issue_desc: return of im viewissue
        :type issue_desc: list[string]

        :return: MKS Issue class
        :rtype: Object of type `ImsIssue` or for old mks tasks of type `MKSData`
        """
        # Parse Issue Type
        issue_type = ""

        for line in issue_desc:
            line = line.split(":", 1)
            if line[0] == 'Type':
                issue_type = line[1]
                issue_type = issue_type.strip()
                break

        # Check after Issue Type
        if issue_type in ["Issue", "Realization Order", "Release", "Analysis Task", "Task"]:
            issue = self.__create_ims_entry(issue_desc)
        else:
            print 'Issue type "%s" unknown' % issue_desc
            issue = None

        return issue


class Im(object):
    """
    The Im-class provides a Interface to the CommandLine Interface of the
    MKS Integrity Manager.

    This class works as a interface between Python and MKS
    to Read out all IMS Items which are typically used inside our Releases.

    It supports IMS commands
        - `connect`
        - `disconnect`
        - `createissue`
        - `copyissue`
        - `viewissue`
        - `editissue`

    Methods for the commands `createissue`, `copyissue` and `editissue` open a GUI from MKS.

    Items read from IMS are stored in type `ImsIssue` derived from dict.
        - keys taken from the output of the viewissue, converted to lower case and space replaced by '_'
        - values as listed behind the first ':', multiline fields recognized by following key in list

        ::
            Type: Issue
            ID: 391582
            Created By: Hospes, Gerd-Joachim (uidv8815)
            Created Date: Oct 29, 2015 10:46:15 AM
            Summary: [STK] fix im modules to work with splitted MKS
            State: Accepted
            Assigned User: Hospes, Gerd-Joachim (uidv8815)
            Project: /Validation_Tools

            dict( type = 'Issue',
            id = '391582',
            created_by = 'Hospes, Gerd-Joachim (uidv8815)',
            created_date = 'Oct 29, 2015 10:46:15 AM',
            summary = '[STK] fix im modules to work with splitted MKS',
            state = 'Accepted',
            assigned_user = 'Hospes, Gerd-Joachim (uidv8815)',
            project = '/Validation_Tools')



    :author:    Robert Hecker
    :date:      26.05.2014
    """
    # pylint: disable=C0103
    def __init__(self):
        self.__parser = ImParser()

    @staticmethod
    def _exe_cmd(arg):  # pylint: disable=R0201
        """
        Executes the command with the given parameters, and returns
        when execution is finished.

        :param arg: Arguments for cli call
        :type arg:  list of strings
        :return:    Error Code from cli call

        :author:        Robert Hecker
        :date:          26.04.2013
        """
        # build cmd line because Popen uses strange handling of ' and " in changing list to cmd line
        cmd = ""
        for el in arg:
            cmd += el
            cmd += " "

        if DEBUG:
            print cmd

        # Execute the command
        proc = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
        out = proc.communicate()[0].splitlines()

        error = proc.returncode

        if error != 0:
            # Get Return String
            raise ImException(error, str(error))

        return out

    def connect(self, user, pwd, hostname="ims-adas", port=7001):
        """
        establishes a connection to an Integrity Server.

        This connection will be used for all other commands till a
        disconnect is done. When the connect method is not used,
        the cli interface try to use a existing connection
        to the mks server. For example over the GUI Interface.
        Multiple Connections for different Servers are not supported,
        you must use disconnect to disconnect from one host before
        establishing a connection to another.

        :param user:     MKS-UserName
        :type user:      string
        :param pwd:      Password for MKS-Server
        :type pwd:       string
        :param hostname: Name, of server used for connection
        :type hostname:  string
        :param port:     Port
        :type port:      int
        :return:         -

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        arg = ["im", "connect", "--hostname=" + hostname, "--port=" + str(port), "--password=" + pwd, "--user=" + user,
               "--quiet", "--batch"]

        # Execute Command
        return self._exe_cmd(arg)

    def disconnect(self):
        """
        disconnects the client connection to the host Integrity Server.

        The disconnect call will disconnect all client connections to
        the Server, also the GUI based connections.

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        arg = ["im", "disconnect", "--forceConfirm=yes", "--quiet", "--batch"]

        # Execute Command
        return self._exe_cmd(arg)

    def createissue(self, issue_type, *args, **fields):
        """
        Create a new issue of given type (Issue, Realisation Order, Release,...)

        **still open**: align format of fields to pass to the command.

        in difference to the returned issue of method viewissue this method expects for the fields
        a dict with keys similar to original IMS keys expected.

            instead of 'assigned_user' the key for this has to be 'Assigned User'

        :param issue_type: type of the issue like 'Change Request', 'Realization Order' etc.,
                           no check here if request is allowed in current state of issue, using for im result
        :type  issue_type: str
        :param args:  additional arguments
        :type args:   str
        :param fields:  additional parameters to add as --field entry
        :type fields:   dict
        :returns: output (error msg) of im command
        :rtype:   str
        """
        arg = ['im', 'createissue', '-g', '--type=%s' % issue_type]
        arg.extend([i for i in args])
        for kw in fields.keys():
            arg.append(''.join(['--field="', kw, '=', fields[kw], '"']))

        ret = self._exe_cmd(arg)

        return ret

    def viewissue(self, issue_id):
        """
        Provides all available information about a MKS Issue from the given
        issue id.

        :param issue_id:   Issue Identifier, from where you want to have the info
        :type issue_id:    int
        :return:           IMS item
        :rtype:            Instance of `ImsIssue` (or `MksCr` etc. for old MKS items)

        :author:           Robert Hecker
        :date:             03.06.2014
        """
        arg = ["im", "viewissue", "--hostname", "ims-adas", str(issue_id)]

        # Execute Command
        ret = self._exe_cmd(arg)

        return self.__parser.convert(ret)

    def editissue(self, issueid, *options):
        """
        change given options of an issue calling 'im editissue'

        :param issueid: mks id of issue to change
        :type  issueid: int
        :keyword state: new state of issue, has to be an allowed state in current state of issue
        :type    state: str
        :keyword options: issue field name to set/change, can be repeated
                          possible values for editissue: --field="State=Planned"
        :type    options: str
        :returns: output (error msg) of im command
        :rtype:   str
        """
        arg = ['im', 'editissue', '-g']
        arg.extend([i for i in options])
        # for kw in options.keys():
        #     arg.append(''.join(['--',kw, r'="', options[kw], r'"']))
        arg.append(issueid)

        ret = self._exe_cmd(arg)

        return ret

    def copyissue(self, issueid, issue_type, *args, **fields):
        """
        create a related issue for given id

        :param issueid: mks id of issue to create related issue for
        :type  issueid: int
        :param issue_type: type of the issue like 'Change Request', 'Realization Order' etc.,
                           no check here if request is allowed in current state of issue, using for im result
        :type  issue_type: str
        :param args:  additional arguments
        :type args:   str
        :param fields:  additional parameters to add as --field entry
        :type fields:   str
        :returns: output (error msg) of im command
        :rtype:   str
        """
        arg = ['im', 'copyissue', '-g', '--type="{}"'.format(issue_type)]
        arg.extend([i for i in args])
        for kw in fields.keys():
            arg.append(''.join(['--field="', kw, '=', fields[kw], '"']))
        arg.append(issueid)

        ret = self._exe_cmd(arg)

        return ret


"""
CHANGE LOG:
-----------
$Log: im.py  $
Revision 1.8 2016/03/15 19:32:36CET Hospes, Gerd-Joachim (uidv8815) 
remove old AD_* issues and releases
Revision 1.7 2015/12/07 17:29:14CET Mertens, Sven (uidv7805) 
now the very last pep8 error is gone!
Revision 1.6 2015/12/07 17:05:31CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.5 2015/12/03 17:43:30CET Hospes, Gerd-Joachim (uidv8815)
fix mks/ims keywords after update to ptc 10.6, pylint fixes
Revision 1.4 2015/10/29 14:29:33CET Hospes, Gerd-Joachim (uidv8815)
rem space before viewissue values, extend docu
--- Added comments ---  uidv8815 [Oct 29, 2015 2:29:33 PM CET]
Change Package : 391599:1 http://mks-psad:7002/im/viewissue?selection=391599
Revision 1.3 2015/10/26 16:39:46CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
Revision 1.2 2015/05/21 17:12:49CEST Hospes, Gerd-Joachim (uidv8815)
add createissue
--- Added comments ---  uidv8815 [May 21, 2015 5:12:50 PM CEST]
Change Package : 336934:1 http://mks-psad:7002/im/viewissue?selection=336934
Revision 1.1 2015/04/23 19:04:33CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/mks/project.pj
Revision 1.5 2015/03/19 18:41:00CET Hospes, Gerd-Joachim (uidv8815)
add editissue and copyissue, no tests yet
--- Added comments ---  uidv8815 [Mar 19, 2015 6:41:00 PM CET]
Change Package : 319757:1 http://mks-psad:7002/im/viewissue?selection=319757
Revision 1.4 2015/03/13 15:21:50CET Hospes, Gerd-Joachim (uidv8815)
support ims release as dict
--- Added comments ---  uidv8815 [Mar 13, 2015 3:21:50 PM CET]
Change Package : 311672:1 http://mks-psad:7002/im/viewissue?selection=311672
Revision 1.3 2015/01/16 15:15:43CET Hospes, Gerd-Joachim (uidv8815)
add error if no release issue type and AD_FR field
Revision 1.2 2014/07/24 14:47:50CEST Hecker, Robert (heckerr)
Added Documentation.
BugFix for CR Parsing.
--- Added comments ---  heckerr [Jul 24, 2014 2:47:50 PM CEST]
Change Package : 251296:1 http://mks-psad:7002/im/viewissue?selection=251296
Revision 1.1 2014/07/14 11:28:24CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/
    mks/project.pj
"""
