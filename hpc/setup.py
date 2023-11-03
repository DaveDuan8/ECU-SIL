"""
setup.py
--------

build a wheel package out of HPC_two
"""
# - Python imports -----------------------------------------------------------------------------------------------------
import sys
from os import makedirs, getcwd, listdir, getenv
from os.path import isdir, dirname, join, abspath, exists
from shutil import rmtree, move, ignore_patterns
from ast import iter_child_nodes, parse, Assign
from setuptools import setup, find_packages


# - main ---------------------------------------------------------------------------------------------------------------
def _recur_copy(src, dst, ignore=None):
    """copy files"""
    if isdir(src):
        if not isdir(dst):
            makedirs(dst)

        files = listdir(src)
        if ignore is not None:
            ignored = ignore(src, files)
        else:
            ignored = set()
        for fname in files:
            if fname not in ignored:
                _recur_copy(join(src, fname), join(dst, fname), ignore)
    else:
        print("cp {} -> {}".format(src, dst))
        move(src, dst)


def _file_arrange():
    """arrange source files on Linux"""
    base_fldr = dirname(abspath(__file__))

    if sys.platform == "win32":
        return base_fldr

    dst = join(base_fldr, "hpc")
    if not exists(dst):
        _recur_copy(base_fldr, dst, ignore_patterns("__pycache__", "*.pyc", "Jenkinsfile", "hpc", "docs", ".*",
                                                    "setup.py", "venv"))
        for i in ("bpl", "cmd", "core", "docs", "mts", "rdb", "sbmt", "sched",):
            rmtree(join(base_fldr, i))
    return dst


def _setitup():  # pylint: disable=R1260
    """set it up"""
    base_fldr = _file_arrange()
    if base_fldr == getcwd():
        print("please, run setup.py from a folder above under windows!")
        return 1

    with open(join(base_fldr, "README.md"), encoding="utf-8") as fp:
        long_description = fp.read()

    version = {"MAJOR": 0, "MINOR": 0, "FIX": 0}
    with open(join(base_fldr, "version.py")) as fp:
        for node in iter_child_nodes(parse(fp.read())):
            if isinstance(node, Assign) and node.targets[0].id in version.keys():
                version[node.targets[0].id] = node.value.n

    version = "{MAJOR}.{MINOR}.{FIX}".format_map(version)
    if not getenv("TAG_NAME"):
        print("only runnable under and from Jenkins!")
        return 1
    if version != getenv("TAG_NAME"):
        print("version from package and GitHub tag do not match: {} vs {}!".format(version, getenv("TAG_NAME")))
        return 1

    with open(join(base_fldr, "requirements.txt")) as fp:
        reqs = [i for i in fp.readlines() if i or "azure" not in i]

    for fldr in ("build", "dist", "hpc.egg-info",):
        try:
            rmtree(fldr)
        except Exception:
            pass

    if len(sys.argv) == 1:
        sys.argv.extend(["bdist_wheel", "--universal"])

    setup_args = {"name": "hpc",
                  "version": version,
                  "author": "HPC team",
                  "author_email": "azure_hpc_data_processing.au_ww_sa@continental-corporation.com",
                  "description": "HPC Python package",
                  "long_description": long_description,
                  "long_description_content_type": "text/markdown",
                  "url": "https://github-am.geo.conti.de/ADAS/HPC_two",
                  "download_url": "https://github-am.geo.conti.de/ADAS/HPC_two/archive/{}.tar.gz".format(version),
                  "project_urls": {"Bug Tracker": "https://jira-adas.zone2.agileci.conti.de/secure/CreateIssueDetails!"
                                                  "init.jspa?pid=12326&issuetype=10000&priority=3"
                                                  "&summary=[issue+description]&assignee=uidv7805"
                                                  "&customfield_10114=13464"},
                  "classifiers": [
                      "Programming Language :: Python :: 2.7",
                      "Programming Language :: Python :: 3",
                      "License :: Continental",
                      "Operating System :: OS Independent",
                  ],
                  "packages": find_packages(".", exclude=("examples", "testing*", "sphinx",)),
                  "package_data": {"": ['hpc_docu.chm']},
                  "python_requires": ">=2.7.17",
                  "install_requires": reqs
                  }

    if sys.platform != "win32":
        setup_args["package_dir"] = {"hpc": base_fldr}

    setup(**setup_args)

    return 0


if __name__ == "__main__":
    sys.exit(_setitup())
