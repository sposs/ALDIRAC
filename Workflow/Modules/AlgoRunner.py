# -*- coding: utf-8 -*-
"""
Created by stephanep on 13.05.15

Copyright 2015 Alpes Lasers SA, Neuchatel, Switzerland
"""
__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_OK, S_ERROR, gLogger
import os
import shutil


class AlgoRunner(ModuleBase):
    def __init__(self):
        super(AlgoRunner, self).__init__()
        self.log = gLogger.getSubLogger("AlgoRunner")
        self.algo_name = ""
        self.algo_cfg = ""

    def applicationSpecificInputs(self):
        if not self.algo_name:
            return S_ERROR("algo_name not specified")
        if not self.OutputFile:
            self.OutputFile = "algorunner.json"
        return S_OK()

    def applicationSpecificMoveBefore(self):
        if self.algo_cfg:
            algo_cfg = os.path.basename(self.algo_cfg)
            if os.path.exists(os.path.join(self.basedirectory, algo_cfg)):
                shutil.copy(os.path.join(self.basedirectory, algo_cfg), algo_cfg)
                self.algo_cfg = algo_cfg

    def runIt(self):
        try:
            from algorunner_basealgo.localrun.main import Runner
            from algorunner_basealgo.utils.exceptions import NoResult, TimeOut
        except ImportError:
            self.log.error("Cannot import Runner")
            return S_ERROR("Cannot import Runner")

        r = Runner()
        try:
            r.set_input_data(self.InputData)
            r.set_algo_name(self.algo_name)
            if self.algo_cfg:
                r.set_run_config(self.algo_cfg)
            r.set_algorithm_config(self.SteeringFile)
            r.set_output_path(self.OutputFile)
        except Exception as error:
            self.log.error(error)
            return S_ERROR(error)
        try:
            r.run()
        except NoResult:
            self.log.warn("NoResult raised")
        except TimeOut:
            self.log.error("Timeout reached")
            return S_ERROR("TimeOut reached")
        except Exception as error:
            self.log.error(str(error))
            return S_ERROR(str(error))
        r.write_output()

        if not os.path.exists(self.OutputFile):
            self.log.error("Missing output file")
            return S_ERROR("Missing output file")

        return S_OK()