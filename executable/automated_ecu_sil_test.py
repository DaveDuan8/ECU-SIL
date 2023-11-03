import argparse
from colorama import Fore, Style

_projects = ["ARS510VW19"]
_prj = None
_project = None


class Error:

    def __init__(self, msg, error_type):
        if error_type is not None:
            if error_type == "argument":
                self.argument_error(msg)
            else:
                self.error_msg("Unkown Error: " + msg)
                exit(99)
        else:
            self.error_msg("Unspecified Error: " + msg)
            exit(1)

    @staticmethod
    def error_msg(msg):
        print(Fore.RED + msg)
        print(Style.RESET_ALL)

    def argument_error(self, msg):
        self.error_msg("ARGUMENT Error: " + msg)
        exit(2)


class LoadProject:

    def __init__(self, project):
        global _project, _projects, _prj
        if len(project) > 0:
            _project = project
        else:
            Error("Empty argument 'project' is not allowed", error_type="argument")
        not_supported = True
        for prj in _projects:
            if _project.lower() == prj.lower():
                not_supported = False
                print _project.lower()
                module = __import__("custom." + prj)
                tmp = getattr(module, prj)
                _prj = getattr(tmp, prj)()
        if not_supported:
            Error("Project='" + _project + "' is not supported!", error_type="argument")

if __name__ == '__main__':
    """ The main entry point from the command line. """
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="project name, e.g. ARS510VW19")
    parser.add_argument("--label", help="labeled project state, e.g. legacy: AL-CP: AL_ARS510VW19_04.00.00_INT-42")
    parser.add_argument("--dev_path", help="dev path for the checkin of the reports only needed if project"
                                           " and dev path are different")
    parser.add_argument("--recordings", help="BPL-File including full path or base path to the ECU-SIL Recordings then"
                                             " the bpl will be created automatically")
    parser.add_argument("--changepackage", help="ID from the changepackage to check in the reports")
    parser.add_argument("--environment_path", help=r"This argument is only needed, if not the standard path "
                                                   r"D:\Sandboxes\automatedECUSIL should be used")
    args = parser.parse_args()

    LoadProject(args.project)

    if args.dev_path is None:
        args.dev_path = args.project

    # execute the different step after each other

    # create environment for testing and checkin ( and sync needed files)
    # e.g. the AL-CP sandbox (SIL environment) + DEV-Path (checkin environment)
    if args.environment_path is None:
        _prj.get_environment(args.label, args.project, args.dev_path)
    else:
        _prj.get_enviroment(args.label, args.project, args.dev_path, args.environment_path)
    # collect the input data for the ECU-SIL test
    #  e.g. the bpl with the used recordings as input for MTS
    _prj.provide_data_list(args.recordings)

    # create/modify the needed configurations which components have to simulated, merging with the exporter,
    #  set project specific parameters (e.g. switch off overulers) ...
    _prj.prepare_simulation()

    # execute the simulation on a local pc (best case a remote-workingstation)
    # because so the it s clear that the execution is direct and not queded
    _prj.run_simulation()

    # create the ECU SIL reports
    _prj.create_report()

    # check in the created reports
    _prj.check_in_report(args.changepackage)
