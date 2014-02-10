#!/bin/env python
import os
import math
import subprocess

if __name__ == "__main__":
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    
    from DIRAC import exit as dexit
    from DIRAC import rootPath
    from DIRAC import gConfig
    
    from DIRAC.ConfigurationSystem.Client.Helpers.CSGlobals import getCSExtensions

    from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
    ops = Operations()
    
    scaling_factor = ops.getValue("JobAgent/ScalingFactor", 28./32)
    etcpath = os.path.join(rootPath, "etc", "dirac.cfg")
    
    #now fetch the number of processors
    try:
        res = subprocess.check_output(["grep","processor","/proc/cpuinfo"])
        n_cores = len(res.split("\n")) - 1
    except:
        #fall back, assume only one core, too bad if there are many more
        n_cores = 1
        
    if n_cores > 1:
        n_agents = math.floor(scaling_factor*n_cores)
    else:
        n_agents = 1
    
    from DIRAC.ConfigurationSystem.Client.Helpers.CSGlobals import getSetup
    
    success = False
    from DIRAC.Core.Utilities.InstallTools import setupComponent
    for n_agent in range(n_agents):
        
        gConfig.setOptionValue("/Systems/WorkloadManagement/%s/Agents/JobAgent_%s/Module" % (getSetup(), n_agent), "JobAgent")
        gConfig.dumpLocalCFGToFile(etcpath)
        #Now that the etc/dirac.cfg was modified, refresh the config in memory.
        gConfig.loadFile(etcpath)
        
        res = setupComponent("agent", "WorkloadManagement", "JobAgent_%s" % n_agent, getCSExtensions())
        if not res["OK"]:
            print "Failed to setup a JobAgent instance"
        else:
            success = True
    if not success:
        print "Could not start any JobAgents"
        dexit(1)
    dexit(0)
