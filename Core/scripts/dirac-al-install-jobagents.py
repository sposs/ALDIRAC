#!/bin/env python
import os
import math
import subprocess
import stat
import time

default_perms = stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH

if __name__ == "__main__":
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    
    from DIRAC import exit as dexit
    from DIRAC import rootPath
    from DIRAC import gConfig
    from DIRAC import gLogger
    from DIRAC.ConfigurationSystem.Client.Helpers.CSGlobals import getCSExtensions

    from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
    ops = Operations()
    
    #imageName = 
    #scaling_factor = gConfig.getValue("/Resources/VirtualMachines/RunningPods/%s/CPUPerJobScaling" % imageName, 25./32)
    
    scaling_factor = ops.getValue("JobAgent/ScalingFactor", 25./32)#not 1: we want to leave some space for the Agent to run
    if scaling_factor > 1:
        scaling_factor = 1
    #etcpath = os.path.join(rootPath, "etc", "dirac.cfg")#don't need this as we are not touching the local config
    
    #now fetch the number of processors
    try:
        res = subprocess.Popen(["grep","processor","/proc/cpuinfo"], stdout = subprocess.PIPE).communicate()
        n_cores = len(res[0].split("\n")) - 1
    except:
        #fall back, assume only one core, too bad if there are many more
        n_cores = 1
    gLogger.notice("Found %s cores" % n_cores)    
    if n_cores > 1:
        n_agents = int(math.floor(scaling_factor*n_cores))
    else:
        n_agents = 1
    gLogger.notice("Will start %s agents" % n_agents)
    success = False
    for n_agent in range(n_agents):
        ## commented out as those possibly ~30 agents are already defined in the central CS
        #gConfig.setOptionValue("/Systems/WorkloadManagement/%s/Agents/JobAgent_%s/Module" % (getSetup(), n_agent), "JobAgent")
        #gConfig.dumpLocalCFGToFile(etcpath)
        ##Now that the etc/dirac.cfg was modified, refresh the config in memory.
        #gConfig.loadFile(etcpath)
        
        runitCompDir = os.path.join( rootPath, "runit", "WorkloadManagement", "JobAgent%s" %  n_agent )
        componentCfg = os.path.join(rootPath, "etc", "WorkloadManagement_JobAgent%s.cfg" % n_agent)
        try:
            fd = open(componentCfg, "w")
            fd.close()
        except OSError:
            continue
        logDir = os.path.join( runitCompDir, 'log' )
        try:
            os.makedirs(logDir)
        except OSError:
            continue
        logConfigFile = os.path.join( logDir, 'config' )
        try:
            fd = open( logConfigFile, 'w' )
            fd.write( 
"""s10000000
n20
""" )
            fd.close()
        except OSError:
            continue
        logRunFile = os.path.join( logDir, 'run' )
        try:
            fd = open( logRunFile, 'w' )
            fd.write( 
"""#!/bin/bash
#
rcfile=%(bashrc)s
[ -e $rcfile ] && source $rcfile
#
exec svlogd .

""" % { 'bashrc' : os.path.join( rootPath, 'bashrc' ) } )
            fd.close()
        except OSError:
            continue 
        os.chmod( logRunFile, default_perms )
        
        runFile = os.path.join( runitCompDir, 'run' )
        try:
            fd = open( runFile, 'w' )
            fd.write( 
"""#!/bin/bash
rcfile=%(bashrc)s
[ -e $rcfile ] && source $rcfile
#
exec 2>&1
#
renice 20 -p $$
#
mkdir -p /tmp/jobAgent-$$
chown dirac:dirac /tmp/jobAgent-$$
cd /tmp/jobAgent-$$
exec python $DIRAC/DIRAC/Core/scripts/dirac-agent.py WorkloadManagement/JobAgent%(n_agents)s %(componentCfg)s < /dev/null
""" % {'n_agents':n_agent, 'bashrc': os.path.join( rootPath, 'bashrc' ),
       'componentCfg': componentCfg } )
            fd.close()
        except OSError:
            continue
        os.chmod( runFile, default_perms )
        startCompDir = os.path.join( rootPath, "startup", 'WorkloadManagement_JobAgent%s' % ( n_agent ) )
        if not os.path.lexists( startCompDir ):
            try:
                os.symlink( runitCompDir, startCompDir )
            except:
                continue
            time.sleep( 5 )
        success = True
    if not success:
        print "Could not start any JobAgents"
        dexit(1)
    dexit(0)
