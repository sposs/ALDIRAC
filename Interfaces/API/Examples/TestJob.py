#!/usr/bin/env python
from ALDIRAC.Interfaces.API.Applications import SewlabPostProcess

if __name__  == "__main__":
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    from ALDIRAC.Interfaces.API.Applications import Sewlab
    from ALDIRAC.Interfaces.API.Dirac import Dirac
    from ALDIRAC.Interfaces.API.UserJob import UserJob
    from DIRAC import gLogger, exit as dexit
    efield = -50
    d = Dirac(True, "repo.rep")
    j = UserJob()
    j.setName("Test")
    j.setJobGroup("test")
    j.setCPUTime(1000)
    j.setOutputSandbox(["*.log","*.pkl"])

    s = Sewlab()
    s.setSteeringFile("test.xml")
    s.setAlteredParameters("efield = %s" % efield)
    s.setOutputFile("temp.dat")
    res = j.append(s)
    if not res["OK"]:
        gLogger.error(res["Message"])
        dexit(1)
        
    sewlab_post = SewlabPostProcess()
    sewlab_post.getInputFromApp(s)
    sewlab_post.setOutputFile("efield_%s.pkl" % (efield))
    res = j.append(sewlab_post)
    if not res["OK"]:
        gLogger.error(res["Message"])
        dexit(1)    
    j.setLogLevel("VERBOSE")
    res = j.submit(d, mode="local")
    
    if not res['OK']:
        gLogger.error(res["Message"])
        dexit(1)
    else:
        gLogger.notice("JobIDs:", res['Value'])
        dexit()
