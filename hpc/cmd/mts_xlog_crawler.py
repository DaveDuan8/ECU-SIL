"""
mts_xlog_crawler.py
-------------------

MTS Xlog Crawler scans a hpc file system to extract data from xlog files and save to csv file

1. select a head node
2. map head node with file system
3. scan a file system to find a job folders
4. find a xlog file in job folders
5. parse xlog file to extract data for error and exception
6. save extracted data to csv file

"""
from pathlib import Path
from os.path import isdir, join
from datetime import datetime
import xml.etree.ElementTree as et
import argparse
import pandas as pd


HEAD_NODE_FS_MAP = {"OZAS012A": "//ozfs110.oz.in.conti.de/hpc/OZAS012A",
                    "LU00156VMA": "//LUFS009X.li.de.conti.de/hpc/LU00156VMA",
                    "QHS6U5CA": "//qhfs004x.qh.us.conti.de/hpc/QHS6U5CA"}
MTS_PATH = "1_Input/mts"
MTS_SYSTEM = "1_Input/mts_system"
DATETIME = datetime.now().strftime('_%d_%m_%Y_%H_%M_%S')


def mts_xlog_crawler(headnode):
    """Its scans file system and find a mts xlog files in job folders"""
    fs = HEAD_NODE_FS_MAP[headnode]
    print("scanning to %s" % fs)
    hpc_share = Path(fs)
    hpc_jobs = [job_dir for job_dir in hpc_share.iterdir() if hpc_share.is_dir()]
    xlog_files = []
    print("total no of jobs found %d" % len(hpc_jobs))
    print("finding a mts xlog files in jobs")
    for hpc_job in hpc_jobs:
        if isdir(join(str(hpc_job), MTS_PATH)) or isdir(join(str(hpc_job), MTS_SYSTEM)):
            tasks = sorted(Path(join(str(hpc_job), '2_Output')).rglob('T*'))
            for task in tasks:
                if isdir(join(str(task), 'log')):
                    mts_xlog_file_path = sorted(Path(join(str(task), 'log')).rglob('*.xlog'))
                    if mts_xlog_file_path:
                        xlog_files.append(str(mts_xlog_file_path[0]))
                    else:
                        print("MTS xlog file not found")
                else:
                    print("MTS log directory doesn't exist")
        else:
            print("MTS directory doesn't exist for this job: %s" % join(str(hpc_job)))
    # parsing xlog file and error and exception data extracted from xlog file
    error, exception = mts_xlog_parser(xlog_files)
    # save data into csv file
    xlog_writer(headnode, error, exception)


def mts_xlog_parser(xlog_files):
    """
    parse xlog file and error and exception extracted from xlog file

    :param list xlog_files: list of files to parse through
    :return: error and exception data found
    :rtype: tuple
    """
    try:
        print("MTS xlog file parsing...")
        error_data = []
        exception_data = []
        for xlog_file in xlog_files:
            try:
                tree = et.parse(xlog_file)
                root = tree.getroot()
                for child in root.iter('LogEntry'):
                    if child.attrib["Severity"] == 'Error':
                        error_data.append(child.text)
                    elif child.attrib["Severity"] == 'Exception':
                        exception_data.append(child.text)
                    else:
                        pass
            except et.ParseError:
                pass
        print("error and exception data extracted from xlog files")
        return error_data, exception_data
    except et.ParseError:
        pass


def xlog_writer(headnode, error_data, exception_data):
    """
    save extracted data into csv file

    :param str headnode: name of head
    :param list error_data: TODO
    :param list exception_data: TODO
    """
    print("saving extracted data into csv file")
    xlog_data = {"Severity_Error": list(set(error_data)), "Severity_Exception": list(set(exception_data))}
    df = pd.DataFrame.from_dict(xlog_data, orient='index')
    df = df.transpose()
    df.to_csv(headnode + DATETIME + ".csv")


if __name__ == '__main__':

    opts = argparse.ArgumentParser()
    opts.add_argument("-n", "--headnode", help="headnode example: OZAS012A")
    args = opts.parse_args()
    mts_xlog_crawler(args.headnode)
