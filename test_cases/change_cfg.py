import sys
import os
import stat
import json
if __name__ == "__main__":
    print
    print ("get simulation cfg")
    sim_switch = "sim"
    component = "fusion"
    # Check number of parameters


    print ("- Parameter 1: input: algo_all_sub.simcfg")
    print ("- Parameter 2: output modified algo_all_sub.simcfg")


    # Get parameters
    Filename_build_in = "algo_all_sub.simcfg"
    Filename_build_out = "algo_all_sub.simcfg"
    # read simcfg
    print ("Read %s" % (Filename_build_in,))
    sim_cfg = open(Filename_build_in, "r").read()
    # Remove read only
    os.chmod(Filename_build_in, stat.S_IWRITE)

    # Change component simulation cfg
    print ("Changing configuration")
    if sim_switch == "meas":
        if sim_cfg.find(component + "_sim_sub.simcfg") >= 0:
            sim_cfg = sim_cfg.replace(component + "_sim_sub.simcfg", component + "_sim_sub_meas.simcfg")
            open(Filename_build_out, "w").write(sim_cfg)
        else:
            if sim_cfg.find(component + "_sim_sub_meas.simcfg") >= 0:
                print( "no change is needed in file")
            else:
                print ("Error: replace error, check the simcfg file")
                sys.exit(1)

    if sim_switch == "sim":
        if sim_cfg.find(component + "_sim_sub_meas.simcfg") >= 0:
            sim_cfg = sim_cfg.replace(component + "_sim_sub_meas.simcfg", component + "_sim_sub.simcfg")
            open(Filename_build_out, "w").write(sim_cfg)
        else:
            if sim_cfg.find(component + "_sim_sub_meas.simcfg") >= 0:
                print( "no change is needed in file")
            else:
                print ("Error: replace error, check the simcfg file")
                sys.exit(1)