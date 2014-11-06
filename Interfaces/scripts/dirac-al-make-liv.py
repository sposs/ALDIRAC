#!/usr/bin/env python

from DIRAC.Core.Base import Script
from DIRAC import S_OK


class CliParams(object):
    def __init__(self):
        super(CliParams, self).__init__()
        self.design = ""
        self.steps = 0
        self.initial_efield = 0
        self.final_efield = 0
        
    def setDesign(self, opt):
        self.design = opt
        return S_OK()

    def setSteps(self, opt):
        self.steps = opt
        return S_OK()

    def setInitialEfield(self, opt):
        self.initial_efield = opt
        return S_OK
    def setFinalEfield(self, opt):
        self.final_efield = opt
        return S_OK

    def registerSwitches(self):
        Script.registerSwitch("d:", 'design=', "The design ID", self.setDesign)
        Script.registerSwitch("s:", "steps=", "Number of steps", self.setSteps)
        Script.registerSwitch("i:", "initial=", "Starting efield", self.setInitialEfield)
        Script.registerSwitch("f:", "final=", "Final efield", self.setFinalEfield)
        Script.setUsageMessage("%s -d 100 -s 10 -e -40" % Script.scriptName)
    
if __name__ == '__main__':
    cli = CliParams()
    cli.registerSwitches()
    Script.parseCommandLine()
    
    from DIRAC import gLogger, exit as dexit
    
    if not cli.design:
        gLogger.error("Missing design")
        dexit(1)
    
    from ALDIRAC.Interfaces.API.UserJob import UserJob
    from ALDIRAC.Interfaces.API.Applications import Sewlab, SewlabPostProcess
    from ALDIRAC.Interfaces.API.Dirac import Dirac
    
    d = Dirac(True, "%s.rep" % cli.design)
    
    j = UserJob()
    j.setCPUTime(700)
    j.setName("%s_efield_%s")
    j.setJobGroup("%s_LIV" % cli.design)
    j.setGenericParametricInput([])
    
    sewlab = Sewlab()
    sewlab.setParametricVariationOn("efield")

    sewlab.setSteeringFile("")
    sewlab.setOutputFile("output.dat")
    res = j.append(sewlab)
    if not res["OK"]:
        gLogger.error(res['Message'])
        dexit(1)
    #postprocess = SewlabPostProcess()
    #postprocess.getInputFromApp(sewlab)
    #output = "%s.xml" % cli.design
    #postprocess.setOutputFile(output)
    #res = j.append(postprocess)
    #if not res["OK"]:
    #    gLogger.error(res['Message'])
    #    dexit(1)
    
    #j.setOutputSandbox([output, "*.log"])
    
    res = j.submit(d)
    print res
