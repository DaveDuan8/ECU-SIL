"""
mts_xlog_patterns.py
--------------------

This script scans a csv file and find a patterns for error and exceptions
"""
import argparse
from datetime import datetime
import pandas as pd

DATETIME = datetime.now().strftime('_%d_%m_%Y_%H_%M_%S')


def find_patterns_error(data, headnode):
    """
    :param file data: file
    :param str headnode: str
    """
    df1 = pd.read_csv(data)

    df1['Severity_Error'] = df1["Severity_Error"].str.replace(r'\d+', '')

    df1 = df1.drop_duplicates(subset=['Severity_Error'])

    df1.to_csv(headnode+"_Error" + DATETIME + ".csv", columns=['Severity_Error'], index=False)


def find_patterns_exception(data, headnode):
    """
    :param file data: file
    :param str headnode: str
    """
    df2 = pd.read_csv(data)

    df2['Severity_Exception'] = df2["Severity_Exception"].str.replace(r'\d+', '')
    df2['Severity_Exception'] = df2["Severity_Exception"].str.replace(r'x[A-F]+', '')

    df2 = df2.drop_duplicates(subset=['Severity_Exception'])

    df2.to_csv(headnode+'_Exception' + DATETIME + '.csv', columns=['Severity_Exception'], index=False)


if __name__ == '__main__':

    opts = argparse.ArgumentParser()
    opts.add_argument("-d", "--data", help="extracted data from xlog file, ex: .csv")
    opts.add_argument("-n", "--headnode", help="headnode ex: OZAS012A")
    args = opts.parse_args()
    find_patterns_error(args.data, args.headnode)
    find_patterns_exception(args.data, args.headnode)
