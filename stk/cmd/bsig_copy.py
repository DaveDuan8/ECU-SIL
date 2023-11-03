r"""
bsig_copy
---------

*bsig move* copies files from input folder to output folder when being listed inside bpl file
and their base name and component name exist inside input folder.

*call syntax example*
C:\> python bsig_copy.py -b <bpl file> -i <input folder> -o <output folder> -c <components> -t

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:03:44CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath, listdir, getcwd, makedirs
from shutil import copyfile
from xml.etree.ElementTree import parse
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter
from re import match


# - main --------------------------------------------------------------------------------------------------------------
def main():
    """
    just calling the operation and saving the result
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-b", dest="bpl", required=True, type=FileType('rb'), help="input BPL to process")
    opts.add_argument("-c", dest="func", required=True, nargs='+', type=str, help="component name to limit")
    opts.add_argument("-t", dest="tstp", default=False, action="store_true", help="also take care of tstp")
    opts.add_argument("-i", dest="infolder", default=getcwd(), type=str, help="input folder for bsigs")
    opts.add_argument("-o", dest="outfolder", required=True, type=str, help="output folder to copy them to")
    args = opts.parse_args()

    if not opath.exists(args.outfolder):  # create out folder ifn't exists
        makedirs(args.outfolder)

    # open bsig and read files
    bpl = open(args.bpl) if not hasattr(args.bpl, "read") else args.bpl
    recs = [opath.splitext(opath.basename(rec.get("fileName")))[0] for rec in parse(bpl).getroot()]
    bpl.close()

    tstp = "_tstp.bsig"
    cp_cnt, sc_cnt = 0, 0
    patt = '(?i)(?P<base>.*)(?P<exp>_(%s))(\\.bsig)$' % "|".join([f.lower() for f in args.func])

    for fname in listdir(args.infolder):  # go through files
        mtc = match(patt, fname)

        if mtc and mtc.group('base') in recs:  # check if file inside bpl
            # copy bsig for function
            inf = opath.join(args.infolder, fname)
            ouf = opath.join(args.outfolder, mtc.group('base') + ".bsig")
            if opath.exists(ouf):
                sc_cnt += 1
            elif opath.isfile(inf):
                print("copying '%s'" % fname)
                copyfile(inf, ouf)
                cp_cnt += 1

            # now copy related tstp file
            tname = mtc.group('base') + tstp
            inf = opath.join(args.infolder, tname)
            ouf = opath.join(args.outfolder, tname)
            if args.tstp and opath.isfile(inf):
                if opath.exists(ouf):
                    sc_cnt += 1
                elif opath.exists(inf):
                    print("copying '%s'" % tname)
                    copyfile(inf, ouf)
                    cp_cnt += 1

    print('done, copied %d file(s), skipped %d file(s)' % (cp_cnt, sc_cnt))


# - main --------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()


"""
CHANGE LOG:
-----------
$Log: bsig_copy.py  $
Revision 1.1 2015/04/23 19:03:44CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.3 2015/03/17 10:38:37CET Mertens, Sven (uidv7805) 
check output file to not copy again
--- Added comments ---  uidv7805 [Mar 17, 2015 10:38:37 AM CET]
Change Package : 318011:1 http://mks-psad:7002/im/viewissue?selection=318011
Revision 1.2 2015/03/12 17:45:16CET Hospes, Gerd-Joachim (uidv8815)
docu update
--- Added comments ---  uidv8815 [Mar 12, 2015 5:45:16 PM CET]
Change Package : 316700:1 http://mks-psad:7002/im/viewissue?selection=316700
Revision 1.1 2015/02/02 10:23:49CET Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/cmd/project.pj
"""
