"""
bpl_xml.py
----------

class for BPL (xml-style) (BatchPlayList) handling
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from re import split
from lxml.etree import Element, SubElement, tostring
from six import PY2
if PY2:
    from codecs import open  # pylint: disable=W0622

# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_ex import BplException
from .bpl_cls import BplReaderIfc, BplList, BplListEntry
from ..core.tds import DEV_LOC, LND_LOC, LOC_HEAD_MAP, PRODUCTION_HEADS


PRODUCTION_SITES = ",".join([loc for loc in LOC_HEAD_MAP if LOC_HEAD_MAP[loc][0] in PRODUCTION_HEADS])


# - classes ------------------------------------------------------------------------------------------------------------
class BPLXml(BplReaderIfc):
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
        BplReaderIfc.__init__(self, *args, **kwargs)

        self._version = None

        if kwargs.get('loc'):
            self._locs = split(r',|;', kwargs.get("loc"))
        else:
            self._locs = []
        if DEV_LOC in self._locs:
            # Dev server is located in LND, to get the correct files we set this here
            self._locs.remove(DEV_LOC)
            self._locs.append(LND_LOC)

    def read(self):  # pylint: disable=R1260
        """
        Read the whole content of the Batch Play List into internal storage,
        and return all entries as a list.

        :return: List of Recording Objects
        :rtype: `BplList`
        :raises BplException: once file cannot be read
        """
        if isinstance(self.filepath, BplListEntry):
            BplList.append(self, self.filepath)
            self.filepath = self[0].filepath[0]
        else:
            try:
                with open(self.filepath, encoding='utf-8') as fp:
                    self._extract_items(fp)
            except BplException:
                raise
            except Exception as ex:
                raise BplException("'{}' is not a BPL file, because of '{!s}'!".format(self.filepath, ex))

        self._read = True
        return self

    def write(self):
        """
        Write the complete list inside the internal storage into a file.

        :return: written chars
        :rtype: int
        """
        top = Element('BatchList', {"version": self._version} if self._version else {})

        def _recur_add(base, entry):
            """add childs"""
            for ent in entry:
                elem = SubElement(base, ent.tag, ent.attrib)
                _recur_add(elem, ent)

        for rec in self:
            _recur_add(top, rec.entry)

        data = tostring(top, pretty_print=True, encoding='utf-8', standalone=True)
        self._written = len(data)

        if self._fp:
            self._fp.write(data)
        else:
            with open(self.filepath, "wb") as fpo:
                fpo.write(data)

        return self._written
