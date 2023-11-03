"""
bpl_coll.py
-----------

class for BPL (xml-style) (BatchPlayList) handling
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from os import environ
from time import sleep
from getpass import getuser
from re import split
from requests import post, get
from six import PY2
if PY2:
    from StringIO import StringIO  # pylint: disable=E0401
else:
    from io import StringIO

# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_ex import BplException
from .bpl_cls import BplReaderIfc
from ..core.tds import DEV_LOC, LND_LOC, LOC_HEAD_MAP, PRODUCTION_HEADS, PORTAL_URL

# - defines ------------------------------------------------------------------------------------------------------------
PRODUCTION_SITES = ",".join([loc for loc in LOC_HEAD_MAP if LOC_HEAD_MAP[loc][0] in PRODUCTION_HEADS])
BASE_URL = "api.falcon.metadata.conti.open-caedge.com"
PROXIES = {"https": PORTAL_URL + ":3128", "http": PORTAL_URL + ":3128"}


# - classes ------------------------------------------------------------------------------------------------------------
class BPLColl(BplReaderIfc):
    r"""
    Specialized BPL Class which handles only writing and reading of \*.bpl Files.
    This class is not a customer Interface, it should only be used internal of hpc.
    """

    def __init__(self, *args, **kwargs):
        """
        init collection, as it can and will be recursive, we call ourself again and again and again

        :param tuple args: args for the interface
        :param dict kwargs: kwargs, loc is taken out immediately, others are passed through
        """
        assert kwargs.pop("mode", "r") == "r", "Only read mode is supported currently"
        BplReaderIfc.__init__(self, *args, **kwargs)

        self._prox = {}

        if kwargs.get('loc'):
            self._locs = split(r',|;', kwargs.get("loc"))
        else:
            self._locs = []
        if DEV_LOC in self._locs:
            # Dev server is located in LND, to get the correct files we set this here
            self._locs.remove(DEV_LOC)
            self._locs.append(LND_LOC)

    def _restore_prox(self):
        """restore proxy envs"""
        for k, v in self._prox.items():
            environ[k] = v

    def read(self):  # pylint: disable=R1260
        """
        Read the whole content of the Batch Play List into internal storage,
        and return all entries as a list.

        :return: List of Recording Objects
        :rtype: `BplList`
        :raises BplException: once file cannot be read
        """
        try:
            self._prox = {k: environ.pop(k) for k in ["HTTP_PROXY", "HTTPS_PROXY"] if k in environ}
            tok = post("https://{}/api_key".format(BASE_URL), json={"user_id": getuser()},
                       allow_redirects=True, verify=False, proxies=PROXIES)
            try:
                tok = tok.json()["api_key"]
            except:
                raise BplException("Response error: {}".format(tok.text))
        except Exception as ex:
            self._restore_prox()
            raise BplException("unable to authenticate ({!s})!".format(ex))

        for i in range(3):
            try:
                sleep(0.2)
                res = get("https://{}/export_collection?collection_name={}".format(BASE_URL, self.filepath),
                          headers={"x-api-key": tok}, allow_redirects=True, verify=False, proxies=PROXIES)
                self._extract_items(StringIO(res.text))
                break
            except BplException:
                raise
            except Exception as ex:
                if i == 2:
                    raise BplException("'{}' didn't work because of '{!s}'!".format(self.filepath, ex))
            finally:
                self._restore_prox()

        self._read = True
        return self

    def write(self):
        """do not write"""
        raise BplException("unable to write by now.")
