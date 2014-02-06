'''
Created on Feb 6, 2014

@author: stephanep
'''
from DIRAC import S_OK, gLogger
from DIRAC.Core.Security.ProxyInfo import getVOfromProxyGroup
from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations

import datetime, string, types, os

#############################################################################
def constructUserLFNs(jobID, vo, owner, outputFiles, outputPath):
    """ This method is used to supplant the standard job wrapper output data policy
        for AlpesLasers.  The initial convention adopted for user output files is the following:
        If outputpath is not defined:
        <vo>/user/<initial e.g. s>/<owner e.g. sposs>/<yearMonth e.g. 2010_02>/<subdir>/<fileName>
        Otherwise:
        <vo>/user/<initial e.g. s>/<owner e.g. sposs>/<outputPath>/<fileName>
    """
    initial = owner[:1]
    subdir = str(jobID/1000)  
    timeTup = datetime.date.today().timetuple() 
    yearMonth = '%s_%s' % (timeTup[0], string.zfill(str(timeTup[1]), 2))
    outputLFNs = {}
    if not vo:
        #res = gConfig.getOption("/DIRAC/VirtualOrganization", "ilc")
        res = getVOfromProxyGroup()
        if not res['OK']:
            gLogger.error('Could not get VO from CS, assuming ilc')
            vo = 'ilc'
        else:
            vo = res['Value']
    ops = Operations(vo = vo)
    lfn_prefix = ops.getValue("LFNUserPrefix", "user")
        
    #Strip out any leading or trailing slashes but allow fine structure
    if outputPath:
        outputPathList = string.split(outputPath, os.sep)
        newPath = []
        for i in outputPathList:
            if i:
                newPath.append(i)
        outputPath = string.join(newPath, os.sep)
    
    if not type(outputFiles) == types.ListType:
        outputFiles = [outputFiles]
      
    for outputFile in outputFiles:
        #strip out any fine structure in the output file specified by the user, restrict to output file names
        #the output path field can be used to describe this    
        outputFile = outputFile.replace('LFN:', '')
        lfn = ''
        if outputPath:
            lfn = os.sep+os.path.join(vo, lfn_prefix, initial, owner, outputPath + os.sep + os.path.basename(outputFile))
        else:
            lfn = os.sep+os.path.join(vo, lfn_prefix, initial, owner, yearMonth, subdir, str(jobID)) + os.sep + os.path.basename(outputFile)
        outputLFNs[outputFile] = lfn
    
    outputData = outputLFNs.values()
    if outputData:
        gLogger.info('Created the following output data LFN(s):\n%s' % (string.join(outputData, '\n')))
    else:
        gLogger.info('No output LFN(s) constructed')
      
    return S_OK(outputData)
