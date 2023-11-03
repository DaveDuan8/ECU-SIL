"""
sched_rest.py
-------------

taken kindly from https://github-am.geo.conti.de/ADAS/DS-SCP/blob/master/Dalib_DataAdminLibrary/src/infrastructure/
onprem/hpc_rest_submit.py

overview: https://docs.microsoft.com/en-us/previous-versions/windows/desktop/hh560258(v=vs.85)
from xml: https://docs.microsoft.com/en-us/previous-versions/windows/desktop/hh560266(v=vs.85)

"""
# - import modules -----------------------------------------------------------------------------------------------------
from os.path import join, dirname
from time import sleep, time
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from requests import request
from requests.auth import HTTPBasicAuth
from six import iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..core import LOGINNAME, UID_NAME
from ..core.logger import suppress_warnings, HpcPassword
from ..core.error import HpcError
from ..core.tds import server_path, location, LOC_HEAD_MAP, DEVS
from ..core.hpc_defs import JobState
from .base import SchedulerBase, to_string


# - classes ------------------------------------------------------------------------------------------------------------
class RestScheduler(SchedulerBase):  # pylint: disable=R0902
    """
    communicate with HPC cluster through rest API
    that class is intended to replace the .NET based implementation being able to submit something from Linux as well
    """

    def __init__(self, headnode, **kwargs):
        """init me"""
        SchedulerBase.__init__(self, headnode, **kwargs)

        self._location = next((k for k, v in iteritems(LOC_HEAD_MAP) if self._head_node in v), None)
        self._base_dir = server_path(self._head_node)

        # some exceptions: Sven, Cedrik, Mohan, Joachim and our HPC user
        if LOGINNAME not in DEVS:
            loc = location("(unknown)")
            if not self._location:  # or self._location not in [loc, X_SUBMIT_EXC.get(loc)]:
                raise HpcError("it's not allowed to submit a job from {} to {}!".format(loc, self._head_node))

        self._check_df()

        self._headers = {'Content-Type': "application/xml; charset=utf-8", 'api-version': '2012-11-01.4.0'}

        with HpcPassword() as hset:
            self._auth = HTTPBasicAuth(UID_NAME, hset[UID_NAME])

        if self.template != 'Default':
            self.check_template()

        self.update(version=None)

        root = Element('ArrayOfProperty', {"xmlns": "http://schemas.microsoft.com/HPCS2008R2/common"})
        for k, v in self._attr.values():
            if v is not None:
                self._add_prop(root, k, to_string(v))
        self._add_prop(root, "Name", kwargs.get("name"))

        self._submitted = False
        self._jobid = int(fromstring(self._request("Jobs", root).text).text)  # return job ID as integer
        self._state_state = JobState.Configuring

        self._job_state, self._state_cp = JobState.All, None
        self.name = kwargs.get('name')

    def __str__(self):
        """
        :return: nice representation
        :rtype: str
        """
        return "<rest scheduler: head={}, id={}, name={}>".format(self._head_node, self._jobid, self.name)

    @staticmethod
    def _add_prop(root, name, value):
        """add name value pair as xml property"""
        prop = SubElement(root, "Property")
        pname = SubElement(prop, "Name")
        pname.text = name
        pval = SubElement(prop, "Value")
        pval.text = value

    @suppress_warnings
    def _request(self, url, data=None, method="POST", params=None):
        """
        do a request

        :param str url: sub-url to the head node
        :param object data: xml element tree to be send as data
        :param str method: method to be used
        :param list params: list of extra url parameters
        :raises hpc.HpcError: once response it not 200, though failed
        :return: :class:`Response <Response>` object
        :rtype: requests.Response
        """
        if data:
            data = tostring(data, encoding="utf-8").decode("utf-8")
        uri_parm = "api-version=2012-11-01.4.0"
        if params:
            uri_parm = "&".join([uri_parm, params if isinstance(params, str) else "&".join(params)])

        res = request(method, "https://{}.CW01.CONTIWAN.COM/WindowsHPC/{}?{}".format(self._head_node, url, uri_parm),
                      data=data, headers=self._headers, auth=self._auth, proxies={"no_proxy": ".contiwan.com"},
                      allow_redirects=True, verify=False)
        if res.status_code != 200:
            raise HpcError("ERROR during head comm: {}".format(res.text))

        return res

    def submit(self, *_args):  # pylint: disable=R1260,W0221
        """
        configure the job and finalize (submit) it

        :param _args: unused
        """
        # create xml file to be used to reconfigure HPC job
        raw_xml = self._to_xml()
        with open(join(dirname(self._base_dir), "HPC_submit", "job",
                       "{}_{}.xml".format(self._head_node, self._jobid)), "w") as fp:
            fp.write(raw_xml.decode())

        for elm in fromstring(raw_xml):
            if elm.tag == "EnvironmentVariables":
                root = Element('ArrayOfProperty', {"xmlns": "http://schemas.microsoft.com/HPCS2008R2/common"})
                for v in elm:
                    v.tag = "Property"
                    root.append(v)
                self._request("Job/{}/EnvVariables".format(self._jobid), root)
            if elm.tag == "Tasks":
                for i in elm:
                    root = Element('ArrayOfProperty', {"xmlns": "http://schemas.microsoft.com/HPCS2008R2/common"})
                    for k, v in i.items():
                        self._add_prop(root, k, v)
                    tid = int(fromstring(self._request("Job/{}/Tasks".format(self._jobid), root).text).text)

                    root = Element('ArrayOfProperty', {"xmlns": "http://schemas.microsoft.com/HPCS2008R2/common"})
                    for v in i.find("EnvironmentVariables"):
                        v.tag = "Property"
                        root.append(v)
                    self._request("Job/{}/Task/{}/EnvVariables".format(self._jobid, tid), root)

        # do the final commit
        self._request("Job/{}/Submit".format(self._jobid))
        self._submitted, self._state_state = True, JobState.Queued

    def check_template(self):
        """
        check if template is available

        :raises hpc.HpcError: if Default or non-existing template is being used
        """
        res = self._request("JobTemplates", method="GET")

        if self.template not in {i.text for i in fromstring(res.text)} - {"Default"}:
            raise HpcError("error: template '{}' does not exist!".format(self.template))

    def cancel_job(self, message):
        """
        cancel specified job. here, we remove the job from the queue,
        but the job remains in the scheduler.

        :param str message: message to display at HPC Job Manager
        """
        root = Element('string', {"xmlns": "http://schemas.microsoft.com/HPCS2008R2/common"})
        root.text = message[:127]
        self._request("Job/{}/Cancel".format(self._jobid), root, params="Forced=True")

    @property
    def jobstate(self):
        """
        :return: state of job
        :rtype: int
        """
        res = self._request("Job/{}".format(self._jobid), method="GET")
        for i in fromstring(res.text):
            if i[0].text == "State":
                self._state_state = int(JobState(i[1].text))
                break

        return self._state_state

    def wait_until_finished(self, **kwargs):
        r"""
        wait until job finishes

        :keyword \**kwargs:
            * *timeout* (``int``): wait timeout [s]
            * *interval* (``int``): interval time [s]
        :return `JobState`: final state of job
        """
        if self._submitted:
            ostate = self._state_state
            timeout = time() + kwargs.get("timeout", 12 * 24 * 60 * 60)
            self._logger.info("waiting until max (%s | finished | failed | canceled)....", "{:.0f}s".format(timeout))

            while True:
                if self.jobstate != ostate:
                    self._logger.info("job state changed from %s to %s",
                                      str(JobState(ostate)), str(JobState(self._state_state)))
                    ostate = self._state_state

                if time() > timeout or self.jobstate in (JobState.Finished, JobState.Failed, JobState.Canceled,):
                    break
                sleep(max(kwargs.get("interval", 24), 12))

        return self._state_state

    # def _set_jattr(self, name, value):
    #     """set a job attribute"""
    #     root = Element('ArrayOfProperty', {"xmlns": "http://schemas.microsoft.com/HPCS2008R2/common"})
    #     self._add_prop(root, name, to_string(value))
    #     res = self._request("Job/{}".format(self._jobid), root)
    #     # tid = int(fromstring(self._request("Job/{}".format(self._jobid), root).text).text)
