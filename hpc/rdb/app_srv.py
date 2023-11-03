"""
app_srv.py
----------

application server connection handler
"""
# - Python imports ----------------------------------------------------------------------------------------------------
from pickle import loads as ploads
from simplejson import dumps
from six import PY2
if PY2:
    from collections import Iterable
    from urllib2 import urlopen, quote  # pylint: disable=E0401
else:  # pragma: no cover
    from collections.abc import Iterable  # pylint: disable=C0412
    from urllib.request import urlopen
    from urllib.parse import quote


# - HPC imports -------------------------------------------------------------------------------------------------------


# - classes / functions -----------------------------------------------------------------------------------------------
class Connection(object):
    """application server connection"""

    def __init__(self, host, schema, **_kwargs):
        """
        take essential info here

        :param str host: host to use / contact for remote connection
        :param str schema: default schema name
        :param dict _kwargs: *unused*
        """
        self._htbase = "{}?schema={}&".format(host, schema)

    def close(self):
        """pseudo closing the connection"""

    def __call__(self, stmt, **kwargs):
        """
        execute a statement by sending it to the appserver

        :param str stmt: statement
        :param dict kwargs: usually parameters to statement
        :returns: returned data from DB
        :rtype: list[object]
        """
        # http://hpcportal.conti.de/dbexec?schem=%s
        data = ploads(urlopen("{}sql={}&args={}".format(self._htbase, quote(stmt), quote(dumps(kwargs)))).read())
        return [_conv(i) for i in data]

    # @property
    # def db_type(self):
    #     """
    #     :return: our own connection type
    #     :rtype: int
    #     """
    #     return


connect = Connection  # pylint: disable=C0103


def _conv(obj):
    """conv back"""
    if isinstance(obj, (list, tuple)):
        res = []
        for i in obj:
            if isinstance(i, Iterable) and i[0] == "\0":
                res.append(ploads(i[1:]))
            else:
                res.append(i)
        return res

    return obj
