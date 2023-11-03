"""
mts_xlog_merge.py
-----------------

This script merge mts xlog file for error and exception data collected from HPC clusters

Example:

    > mts_xlog_merge -ler LU00156VMA_Error_28_05_2020_16_39_30.csv -ber OZAS012A_Error_22_05_2020_09_32_52.csv
        -aer QHS6U5CA_Error_28_05_2020_05_20_36.csv -lex LU00156VMA_Exception_28_05_2020_16_39_30.csv
        -bex OZAS012A_Exception_22_05_2020_09_32_52.csv -aex QHS6U5CA_Exception_28_05_2020_05_20_36.csv

"""

import argparse
import sys
from datetime import datetime
import pandas as pd


DATETIME = datetime.now().strftime('_%d_%m_%Y_%H_%M_%S')


def mts_xlog_merge_error(lnd, bng, abh):
    """
    merge xlog data for error

    :param str lnd: csv file
    :param str bng: csv file
    :param str abh: csv file
    :return: 0
    :rtype: int
    """
    ldf = pd.read_csv(lnd)
    bdf = pd.read_csv(bng)
    adf = pd.read_csv(abh)
    edf = pd.concat([ldf, bdf, adf])
    edf.drop_duplicates()
    edf.to_csv('mts_xlog_error_data' + DATETIME + '.csv')
    return 0


def mts_xlog_merge_exception(lndx, bngx, abhx):
    """
    merge xlog data for exception

    :param str lndx: csv file
    :param str bngx: csv file
    :param str abhx: csv file
    :return: 0
    :rtype: int
    """
    lxdf = pd.read_csv(lndx)
    bxdf = pd.read_csv(bngx)
    axdf = pd.read_csv(abhx)
    xdf = pd.concat([lxdf, bxdf, axdf])
    xdf.drop_duplicates()
    xdf.to_csv('mts_xlog_exception_data' + DATETIME + '.csv')
    return 0


if __name__ == '__main__':

    opts = argparse.ArgumentParser(prog='mtx_xlog_merge')
    opts.add_argument("-ler", "--lnd_data", help="xlog error csv file for LND cluster, <headnode>_Error_<dt>.csv")
    opts.add_argument("-ber", "--bng_data", help="xlog error csv file for BNG Cluster, <headnode>_Error_<dt>.csv")
    opts.add_argument("-aer", "--abh_data", help="xlog error csv file for ABH cluster, <headnode>_Error_<dt>.csv")
    opts.add_argument("-lex", "--lndx_data", help="xlog exception csv file LND cluster, <headnode>_Exception_<dt>.csv")
    opts.add_argument("-bex", "--bngx_data", help="xlog exception csv file BNG cluster, <headnode>_Exception_<dt>.csv")
    opts.add_argument("-aex", "--abhx_data", help="xlog exception csv file ABH cluster, <headnode>_Exception_<dt>.csv")
    if len(sys.argv) > 1:
        args = opts.parse_args()
        mts_xlog_merge_error(args.lnd_data, args.bng_data, args.abh_data)
        mts_xlog_merge_exception(args.lndx_data, args.bngxdata, args.abhxdata)
    else:
        opts.print_help()
