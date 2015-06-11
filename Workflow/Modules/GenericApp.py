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


__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"


class GenericApp(ModuleBase):
    def __init__(self):
        super(GenericApp, self).__init__()
        self.log = gLogger.getSubLogger("GenericApplication")
        self.parameters_dict = {}
        self._executable = ""
        self.simudb = SimuDBClient()
        self.taskname = ""

    def applicationSpecificInputs(self):
        if "ApplicationName" not in self.parameters_dict:
            return S_ERROR("Application name was not defined properly")
        self._executable = self.parameters_dict.get("ApplicationName")
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)
        if "OutputFile" not in self.parameters_dict:
            return S_ERROR("Missing Output file definition")
        return S_OK()

    def runIt(self):
        data_file_path = ""
        script_name = "generic_app.sh"
        with open(script_name, "w") as script:
            script.write("#!/bin/bash\n")
            script.write("unset LD_LIBRARY_PATH\n")
            script.write("%s %s\n" % (self._executable, data_file_path))
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
