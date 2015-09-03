# -*- coding: utf-8 -*-
"""
Created by stephanep on 10.06.15

Copyright 2015 Alpes Lasers SA, Neuchatel, Switzerland
"""
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_OK, gLogger, S_ERROR
from DIRAC.Core.Utilities.Subprocess import shellCall
import os
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient
import json
import shutil
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
from DIRAC.Core.Utilities.Os import which

__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"


def find_path_to_app(app):
    """
    Locate an application using different sources of info
    :param app: name of application
    :return: path to binary
    """
    path = ""
    test_path = Operations().getValue("Applications/%s/Path" % app, "")
    if test_path:
        return test_path
    test_path = Operations().getValue("%s/Path" % app, "")
    if test_path:
        return test_path
    path = which(app)
    if path:
        path = os.path.dirname(path)
        return path
    return None


class GenericApp(ModuleBase):
    def __init__(self):
        super(GenericApp, self).__init__()
        self.log = gLogger.getSubLogger("GenericApplication")
        self.parameters_dict = {}
        self._executable = ""
        self.simudb = SimuDBClient()
        self.taskname = ""
        self.execution_module = ""

    def applicationSpecificInputs(self):
        if "Executable" not in self.parameters_dict:
            return S_ERROR("Executable name was not defined properly")
        self._executable = self.parameters_dict.get("Executable")
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)
        if "OutputFile" not in self.parameters_dict:
            return S_ERROR("Missing Output file definition")
        if not self.execution_module:
            return S_ERROR("Execution module name was not defined, cannot run!")

        return S_OK()

    def applicationSpecificMoveBefore(self):
        if self.execution_module:
            exec_module = os.path.basename(self.execution_module)
            if os.path.exists(os.path.join(self.basedirectory, exec_module)):
                shutil.copy(os.path.join(self.basedirectory, exec_module), exec_module)
                self.execution_module = exec_module
                os.chmod(self.execution_module, 0755)  # make it executable

    def runIt(self):
        """
        Need to define a data_file_path properly... Need to find executable location properly too
        :return:
        """
        with open("parameters.json", "w") as param_files:
            param_files.write(json.dumps(self.parameters_dict))
        param_path = os.path.join(os.getcwd(), "parameters.json")
        executable_path = find_path_to_app(self._executable)
        if not executable_path:
            self.log.error("Impossible to find path to binary")
            return S_ERROR("Cannot find path to binary")
        script_name = "generic_app.sh"
        with open(script_name, "w") as script:
            script.write("#!/bin/bash\n")
            script.write("unset LD_LIBRARY_PATH\n")
            exec_str = "%s %s %s" % (self.execution_module, executable_path, param_path)
            if self.InputFile:
                exec_str += " %s" % os.path.basename(self.InputFile)
            exec_str += "\n"
            script.write(exec_str)
            script.write("exit $?\n")
        os.chmod(script_name, 0755)
        cmd = 'sh -c "%s"' % script_name
        self.log.info("Running %s" % cmd)
        self.setApplicationStatus("Running")
        if not self.debug:
            res = self.simudb.setStatus(self.taskname, "running")
            if not res['OK']:
                self.log.error("Failed to set status to running:", res["Message"])
                res = self.simudb.setStatus(self.taskname, "running")
                if not res['OK']:
                    self.log.error("Failed again to set status to running:", res["Message"])
                    self.log.error("Will fail the task")
                    return S_ERROR("Issues with task state machine")

        result = shellCall(0, cmd, callbackFunction=self.redirectLogOutput, bufferLimit=20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            self.report_fail(result["Message"])
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        status = resultTuple[0]
        if status:
            self.log.error("Error with application during run:", resultTuple[1])
            self.report_fail(resultTuple[1])
            return S_ERROR("Error while running")

        self.setApplicationStatus("Success")

        return S_OK()

    def report_fail(self, state):
        if not self.debug:
            res = self.simudb.setStatus(self.taskname, "failed", "Error while executing: %s" % state)
            if not res["OK"]:
                self.log.error("Failed updating task status:", res["Message"])
        else:
            self.log.info("Would have reported task as failed")
