#!/usr/bin/env python
'''
Created on Jun 10, 2014

@author: stephanep
'''
import subprocess
import os
from DIRAC.Core.Utilities.Subprocess import shellCall

def execscript(comm):
    """
    Execute command, and catch if error
    """
    res= shellCall(0, comm)
    if not res['OK']:
        gLogger.error("Failed call", res)
    status  = res['Value'][0]
    
    os.unlink("tmp.sh")
    if status:
        gLogger.error("Issue with call -> ", res['Value'][2])
    return status


def fetch():
    """
    Do a git fetch
    """
    with open("tmp.sh", "w") as script:
        script.write("""#!/bin/bash
unset LD_LIBRARY_PATH
git fetch
exit $?
""")
    os.chmod("tmp.sh", 0755)
    comm = "sh -c './tmp.sh'" 
    return execscript(comm)

def get_version(version):
    """
    Checkout a version
    """
    with open("tmp.sh", "w") as script:
        script.write("""#!/bin/bash
unset LD_LIBRARY_PATH
git checkout refs/tags/%s
exit $?
""" % version)
    os.chmod("tmp.sh", 0755)
    comm = "sh -c './tmp.sh'" 
    return execscript(comm)

if __name__ == '__main__':
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    # First: collect the version
    from DIRAC import gLogger, exit as dexit
    from DIRAC import rootPath
    from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
    ops = Operations()
    aldirac_version = ops.getValue("Cloud/ALDIRAC/Version")
    if not aldirac_version:
        gLogger.error("Missing ALDIRAC version to install")
        dexit(1)
    gLogger.info("Will install ALDIRAC ", aldirac_version)
    dirac_version = ops.getValue("Cloud/ALDIRAC/%s/DiracVersion" % aldirac_version)
    if not dirac_version:
        gLogger.error("Missing DIRAC version")
        dexit(1)
    gLogger.info("Will install DIRAC ", dirac_version)
    
    os.chdir(os.path.join(rootPath, "DIRAC"))
    # do git fetch
    if fetch():
        gLogger.error("Failed")
        dexit(1)
    if get_version(dirac_version):
        gLogger.error("Failed updating DIRAC")
        dexit(1)
    
    os.chdir(os.path.join(rootPath, "ALDIRAC"))
    if fetch():
        gLogger.error("Failed")
        dexit(1)
    if get_version(aldirac_version):
        gLogger.error("Failed updating ALDIRAC")
        dexit(1)
    
    
    
    dexit(0)