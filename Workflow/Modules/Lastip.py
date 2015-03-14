# -*- coding: utf-8 -*-
"""
Created by stephanep on 12.03.15

Copyright 2015 Alpes Lasers SA, Neuchatel, Switzerland
"""
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_OK, S_ERROR, gLogger
import os
import pickle
import cjson
import shutil
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient

__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"


class Lastip(ModuleBase):
    def __init__(self):
        super(Lastip, self).__init__()
        self.log = gLogger.getSubLogger("Lastip")
        self.simudb = SimuDBClient()
        self.taskname = ""
        self.design_xml = ""
        self._run_parameters = {}
        self.run_parameters = ""
        self.simulase_db = ""
        self.parameterchanges = {}

    @staticmethod
    def locate_binary():
        """
        Check that lastip exists
        :return: S_OK, S_ERROR
        """
        if not os.path.exists("/opt/crosslight/lastip-2014/bin/lastip"):
            return S_ERROR()
        return S_OK()

    def applicationSpecificInputs(self):
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)

        self._run_parameters = {}
        if self.run_parameters:
            self._run_parameters = cjson.decode(self.run_parameters)
        if not self.design_xml:
            return S_ERROR("Missing design xml")

        if not self.OutputFile:
            self.OutputFile = "solution_%s.pkl" % self.jobID
            self.parameterchanges["outputfile"] = self.OutputFile
        return S_OK()

    def applicationSpecificMoveBefore(self):
        if self.simulase_db:
            sim_db = os.path.basename(self.simulase_db)
            if os.path.exists(os.path.join(self.basedirectory, sim_db)):
                shutil.copy(os.path.join(self.basedirectory, sim_db), sim_db)
                self.simulase_db = sim_db

        des_xml = os.path.basename(self.design_xml)
        if os.path.exists(os.path.join(self.basedirectory, des_xml)):
            shutil.copy(os.path.join(self.basedirectory, des_xml), des_xml)
            self.design_xml = des_xml
        else:
            return S_ERROR("Cannot find the design XML")
        return S_OK()

    def runIt(self):
        res = self.locate_binary()
        if not res['OK']:
            self.log.error("Cannot find lastip binary in usual location")
            self.report_fail("Cannot find binary")
            return S_ERROR("Cannot find binary")

        try:
            from crosslight_wrapper.server.main import Server
        except ImportError as error:
            self.log.error("Cannot import the wrapper:", str(error))
            return S_ERROR("Cannot import crosslight wrapper")
        if not self.debug:
            res = self.simudb.setStatus(self.taskname, "running")
            if not res['OK']:
                self.log.error("Failed to set status to running:", res["Message"])
                res = self.simudb.setStatus(self.taskname, "running")
                if not res['OK']:
                    self.log.error("Failed again to set status to running:", res["Message"])
                    self.log.error("Will fail the task")
                    return S_ERROR("Issues with task state machine")
        s = Server(host="localhost", local=True)
        session = s.get_new_session(lastip=True)
        try:
            with open(self.design_xml) as indes:
                content = indes.read()
            s.set_design(session, content)
            s.set_run_parameters(session, self._run_parameters)
            if self.simulase_db:
                with open(self.simulase_db, "r") as simdb:
                    content = simdb.read()
                s.set_gain_data(session, content)
            self.setApplicationStatus("Lastip Run")
            s.execute_lastip(session)
            result = s.get_results(session)
            if not result:
                self.log.error("No result returned")
                self.report_fail("Missing result")
                return S_ERROR("No result returned")
            with open(self.OutputFile, "w") as outf:
                pickle.dump(result, outf)
            logs = s.get_logs(session)
            for log, content in logs.items():
                with open(log+".log", "w") as of:
                    of.write(content)
            self.setApplicationStatus("Lastip Done")
        except Exception as error:
            self.report_fail(str(error))
            self.log.exception("Lastip exception")
            return S_ERROR(str(error))
        return S_OK()

    def report_fail(self, state):
        if not self.debug:
            res = self.simudb.setStatus(self.taskname, "failed", "Error while executing lastip: %s" % state)
            if not res["OK"]:
                self.log.error("Failed updating task status:", res["Message"])
        else:
            self.log.info("Would have reported task as failed")