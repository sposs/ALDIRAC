'''
Created on Feb 13, 2014

@author: stephanep
'''
from DIRAC.Core.Base import Script

if __name__ == "__main__":

    Script.parseCommandLine()
    
    from DIRAC import gLogger, exit as dexit
    
    from ALDIRAC.Interfaces.API.UserJob import UserJob
    from ALDIRAC.Interfaces.API.Applications import GenericApplication
    from ALDIRAC.Interfaces.API.Dirac import Dirac
    
    dirac= Dirac(True,'jobrepo.rep')
    
    j = UserJob()
    j.setCPUTime(750)
    j.setJobGroup("Test")
    j.setSubmitPools("Amazon")
    j.setDestination("Cloud.amazon-small.eu")
    j.setName("Test")
    j.setGenericParametricInput("-p %s")
    
    script = open("test.py", 'w')
    script.write("""
#!/usr/bin/env python
from DIRAC.Core.Base import Script

from DIRAC import S_OK, S_ERROR

class CliParam(object):
  def __init__(self):
    self.param = ""
  def setParam(self,opt):
    self.param = opt
    return S_OK()
  def registerOptions(self):
    Script.registerSwitch("p:", "param=", "Starting parameter", self.setParam)
    Script.setUsageMessage("%s -p param" % Script.scriptName)
import time
from math import log

def WasteCPUCycles(timecut):
  a = 1e31
  first = time.clock()
  while time.clock()-first < timecut:
    try:
      a = log(a)
    except Exception, x:
      return S_ERROR("Failed to waste %s CPU seconds:%s" % (timecut, str(x)))  
    if a < 0:
      a = -a
    if a == 0:
      a = 4  
  return S_OK("Successfully wasted %s seconds" % timecut)    

if __name__ == "__main__":
  clip = CliParam()
  clip.registerOptions()
  Script.parseCommandLine()
  from DIRAC import gLogger, exit as dexit

  if not clip.param:
    gLogger.error("Missing parameter")
    #Script.showHelp()
    dexit(1)

  gLogger.notice("Parameter =", clip.param)
  
  res = WasteCPUCycles(700)

""")
    
    app = GenericApplication()
    app.setScript("test.py")
    app.setArguments("-p %s")
    
    result = j.append(app)
    if not result["OK"]:
        gLogger.error("Failed to add job", result['Message'])
        dexit(1)
    
    result = j.submit(dirac)
    if not result['OK']:
        gLogger.error("Failed to submit", result["Message"])
    dexit(0)