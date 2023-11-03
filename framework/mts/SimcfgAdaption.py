class ComponentSetup:
    def __init__(self, base_simcfg_name, simulated):
        self.base_simcfg_name = base_simcfg_name
        self.opposite_simcfg = base_simcfg_name + ".simcfg"
        self.requested_simcfg = base_simcfg_name + ".simcfg"
        if simulated:
            self.opposite_simcfg = base_simcfg_name + "_meas.simcfg"
            self.requested_simcfg = base_simcfg_name + ".simcfg"
        else:
            self.opposite_simcfg = base_simcfg_name + ".simcfg"
            self.requested_simcfg = base_simcfg_name + "_meas.simcfg"
