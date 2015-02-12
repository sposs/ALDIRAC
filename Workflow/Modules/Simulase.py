# -*- coding: utf-8 -*-
"""
Created by stephanep on 15.01.15

Copyright 2015 Alpes Lasers SA, Neuchatel, Switzerland
"""
import os
import shutil
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
from DIRAC.Core.Utilities.Subprocess import shellCall
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient

from DIRAC import S_OK, S_ERROR, gLogger


__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"


class Simulase(ModuleBase):
    """
    Run Simulase via its wrapper
    """
    def __init__(self):
        super(Simulase, self).__init__()
        self.log = gLogger.getSubLogger("Simulase")
        self.design_xml = ""
        self.material_xml = ""
        self.field = 0.
        self.temperature = 300.
        self.polarization = "te"
        self.sheet_density = 10.
        self.broadening = 0.
        self.modifiers = ""
        self.list_modifiers = []
        self.ops = Operations()
        self.license_server_url = self.ops.getValue("Simulase/LicenseURL", "")
        self.simulase_binary_path = ""
        self.simudb = SimuDBClient()
        self.taskname = ""
        self.parameterchanges = {}

    def applicationSpecificInputs(self):
        if not self.OutputFile:
            self.OutputFile = "solution_%s.p" % self.jobID
            self.parameterchanges["outputfile"] = self.OutputFile
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)

        if self.modifiers:
            mods = self.modifiers.split(";")
            for items in mods:
                a, b = items.split("=")
                self.log.info("'%s' = '%s'" % (a, b))
                if a == "profile":
                    if b != "None":
                        self.list_modifiers.append("--profile %s" % b)
                        continue
                if a not in ['skip_auger', "skip_intraband", "profile"]:
                    self.list_modifiers.append("--%s %s" % (a, b))
                else:
                    if b in ['True', "TRUE", 1]:
                        self.list_modifiers.append("--%s" % a)
        return S_OK()

    def applicationSpecificMoveBefore(self):
        if self.material_xml:
            mat_xml = os.path.basename(self.material_xml)
            if os.path.exists(os.path.join(self.basedirectory, mat_xml)):
                shutil.copy(os.path.join(self.basedirectory, mat_xml), mat_xml)
                self.material_xml = mat_xml

        des_xml = os.path.basename(self.design_xml)
        if os.path.exists(os.path.join(self.basedirectory, des_xml)):
            shutil.copy(os.path.join(self.basedirectory, des_xml), des_xml)
            self.design_xml = des_xml
        else:
            return S_ERROR("Cannot find the design XML")
        return S_OK()

    def runIt(self):
        """
        Execute the module content
        :return: S_OK
        """

        bin_dir_env = "%s_%s_DIR" % ("simulase", self.applicationVersion)
        if bin_dir_env not in os.environ:
            self.log.error("Environment doesn't know the Simulase directory")
            return S_ERROR("Environment doesn't know the Simulase directory")
        self.log.info("Software found at ", os.environ[bin_dir_env])
        self.simulase_binary_path = os.environ[bin_dir_env]
        if not os.path.exists(os.path.join(self.simulase_binary_path, "sus.exe")) \
                or not os.path.exists(os.path.join(self.simulase_binary_path, "a3d.exe")) \
                or not os.path.exists(os.path.join(self.simulase_binary_path, "iba.exe")):
            self.log.error("Binaries cannot be found")
            return S_ERROR("Binaries cannot be found")

        if not self.license_server_url:
            self.log.error("Cannot find license server URL")
            return S_ERROR("Cannot find license server URL")


        script_name = self.compile_script()
        comm = 'sh -c "./%s"' % script_name
        self.setApplicationStatus('%s compile step %s' % (self.applicationName, self.STEP_NUMBER))
        if not self.debug:
            res = self.simudb.setStatus(self.taskname, "running")
            if not res['OK']:
                self.log.error("Failed to set status to running:", res["Message"])
                res = self.simudb.setStatus(self.taskname, "running")
                if not res['OK']:
                    self.log.error("Failed again to set status to running:", res["Message"])
                    self.log.error("Will fail the task")
                    return S_ERROR("Issues with task state machine")
        result = shellCall(0, comm, callbackFunction=self.redirectLogOutput, bufferLimit=20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            self.report_fail("compile")
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        status = resultTuple[0]
        if status:
            self.log.error("Error with application during compile", resultTuple[1])
            self.report_fail("compile")
            return S_ERROR("Error in compile step")

        self.setApplicationStatus('%s (%s %s) Successful' % (os.path.basename(script_name),
                                                             self.applicationName, self.applicationVersion))

        script_name = self.run_script()
        comm = 'sh -c "./%s"' % script_name
        self.setApplicationStatus('%s run step %s' % (self.applicationName, self.STEP_NUMBER))
        result = shellCall(0, comm, callbackFunction=self.redirectLogOutput, bufferLimit=20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            self.report_fail("run")
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        status = resultTuple[0]
        if status:
            self.log.error("Error with application during run", resultTuple[1])
            self.report_fail("run")
            return S_ERROR("Error in run step")

        self.setApplicationStatus('%s (%s %s) Successful' % (os.path.basename(script_name),
                                                             self.applicationName, self.applicationVersion))

        script_name = self.post_process()
        comm = 'sh -c "./%s"' % script_name
        self.setApplicationStatus('%s postprocess step %s' % (self.applicationName, self.STEP_NUMBER))
        result = shellCall(0, comm, callbackFunction=self.redirectLogOutput, bufferLimit=20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            self.report_fail("postprocess")
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        status = resultTuple[0]
        if status:
            self.log.error("Error during postprocess", resultTuple[1])
            self.report_fail("postprocess")
            return S_ERROR("Error during postprocess")

        self.setApplicationStatus('%s (%s %s) Successful' % (os.path.basename(script_name),
                                                             self.applicationName, self.applicationVersion))
        return S_OK()

    def compile_script(self):
        script_name = "simulase_compile_%s.sh" % self.STEP_NUMBER
        with open(script_name, "w") as script:
            cmd = ["#!/bin/bash", "unset LD_LIBRARY_PATH"]
            deb_opts = ""
            if self.debug:
                deb_opts = " -D -v"
            path_opts = " -S %s/sus.exe -A %s/a3d.exe -I %s/iba.exe" % (self.simulase_binary_path,
                                                                       self.simulase_binary_path,
                                                                       self.simulase_binary_path,)
            cmd.append("simulase_wrapper compile -o ./compile.p "
                       "-d %s %s %s -s %s -t %s -f %s -p %s -b %s %s"
                       "%s %s" % (self.design_xml, ("-x %s" % os.path.abspath(self.SteeringFile) if self.SteeringFile else ""),
                                  ("-m %s" % os.path.abspath(self.material_xml) if self.material_xml else ""),
                                  self.sheet_density,
                                  self.temperature, self.field, self.polarization, self.broadening,
                                  " ".join(self.list_modifiers),
                                  path_opts, deb_opts))
            self.log.info("Will run", cmd[-1])
            script.write("\n".join(cmd))
        os.chmod(script_name, 0755)
        return script_name

    def run_script(self):
        script_name = "simulase_run_%s.sh" % self.STEP_NUMBER
        with open(script_name, "w") as script:
            cmd = ["#!/bin/bash", "unset LD_LIBRARY_PATH"]
            deb_opts = ""
            if self.debug:
                deb_opts = " -D -v"
            path_opts = " -S %s/sus.exe -A %s/a3d.exe -I %s/iba.exe" % (self.simulase_binary_path,
                                                                       self.simulase_binary_path,
                                                                       self.simulase_binary_path,)
            cmd.append("simulase_wrapper run -l %s -i ./compile.p -o ./run.p "
                       "-w ./run_dir %s %s" % (self.license_server_url, path_opts, deb_opts))
            self.log.info("Will run", cmd[-1])
            script.write("\n".join(cmd))
        os.chmod(script_name, 0755)
        return script_name

    def post_process(self):
        script_name = "simulase_postproc_%s.sh" % self.STEP_NUMBER
        with open(script_name, "w") as script:
            cmd = ["#!/bin/bash", "unset LD_LIBRARY_PATH"]
            deb_opts = ""
            if self.debug:
                deb_opts = " -D -v"
            path_opts = " -S %s/sus.exe -A %s/a3d.exe -I %s/iba.exe" % (self.simulase_binary_path,
                                                                       self.simulase_binary_path,
                                                                       self.simulase_binary_path,)
            cmd.append("simulase_wrapper postprocess -l %s -w ./run_dir -o %s "
                       "%s %s" % (self.license_server_url, self.OutputFile, path_opts, deb_opts))
            self.log.info("Will run", cmd[-1])
            script.write("\n".join(cmd))
        os.chmod(script_name, 0755)
        return script_name

    def report_fail(self, state):
        if not self.debug:
            res = self.simudb.setStatus(self.taskname, "failed", "Error while executing simulase: %s" % state)
            if not res["OK"]:
                self.log.error("Failed updating task status:", res["Message"])
        else:
            self.log.info("Would have reported task as failed")