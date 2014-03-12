'''
Created on Mar 12, 2014

@author: stephanep
'''
from DIRAC.Core.Utilities.ReturnValues import S_OK
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations

def resolveDeps(app, version):
    """ For any application, resolve its dependencies 
    """
    
    ops = Operations()
    res = ops.getSections("/Applications/%s/%s/Depends" % (app, version))
    if not res['OK']:
        return S_OK([])
    deps = res["Value"]
    depdir = []
    
    for dep in deps:
        depdict = {}
        depdict["name"] = dep
        depdict["version"] = ops.getValue("/Applications/%s/%s/Depends/%s/Version" % (app, version, dep), "")
        res = resolveDeps(dep, depdict["version"])
        if res["OK"]:
            depdir.extend(res['Value'])
        depdir.append(depdict)
    return S_OK(depdir)
