"""
Created on May 16, 2014

@author: stephanep
"""
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC.Core.Utilities.ReturnValues import S_OK, S_ERROR
from DIRAC import gLogger
import os
import pickle
import sewlabwrapper.utils.sewlab_convert
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient
from DIRAC.RequestManagementSystem.Client.Request import Request
from DIRAC.RequestManagementSystem.Client.Operation import Operation
import time
import random
from DIRAC.Core.Utilities import DEncode
from DIRAC.RequestManagementSystem.Client.ReqClient import ReqClient


class Analysis(ModuleBase):
    """
    Analysis module: extracts info from the file produced by the SewlabPostProcess
    Send it to the DB if requested by Job.
    """


    def __init__(self):

        super(Analysis, self).__init__()
        self.log = gLogger.getSubLogger("Analysis")
        self.store_output = False
        self.debug = False
        self.simudb = SimuDBClient()
        self.taskname = ""
        
    def applicationSpecificInputs(self):
        if not os.path.exists(self.InputFile[0]):
            return S_ERROR('Missing Input file')
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)
        if self.debug:
            self.log.info("Using debug mode, i.e. do not communicate with SimuDB")
        return S_OK()
    
    def execute(self):
        
        res = self.resolveInputVariables()
        if not res['OK']:
            self.log.error("Error resolving parameters")
            return res
        
        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'],
                                                                         self.stepStatus['OK']))
            return S_OK('Analysis should not proceed as previous step did not end properly')
        try:
            inf = open(self.InputFile[0], "rb")
            resdict = pickle.load(inf)
            inf.close()
        except:
            self.log.error("Couldn't read or unpickle the data")
            return S_ERROR("Failed reading the data")
        i05 = 0
        i085 = 0
        i05b = i085b = 0
        found_05 = found_085 = False
        maxv = max(resdict['solution']['netLLum'])
        i_max = resdict['solution']['netLLum'].index(maxv)
        i = 0
        previous = -1
        for v in resdict['solution']['netLLum']:
            v /= maxv
            #if v<0.5 and found_05 == False:
            #    continue
            if v>0.5:
                if found_05 == False:
                    i05 = i
                    found_05 = True
            if v>0.85:
                if found_085 == False:
                    i085 = i
                    found_085 = True
            if previous > 0.5 and v < 0.5:
                i05b = i-1
            if previous > 0.85 and v < 0.85:
                i085b = i-1
            i += 1
            previous = v
        
        #Send this back to the DB somehow
        lumL_max = resdict['solution']['photonMesh'][i_max]/(0.124e-3)
        lumL_085_min =  resdict['solution']['photonMesh'][i085]/(0.124e-3)
        lumL_085_max =  resdict['solution']['photonMesh'][i085b]/(0.124e-3)
        lumL_05_min = resdict['solution']['photonMesh'][i05]/(0.124e-3)
        lumL_05_max = resdict['solution']['photonMesh'][i05b]/(0.124e-3)
        
        self.log.info("Lum found: max, 0.85_min, 0.85_max, 0.5_min, 0.5_max:", str([lumL_max, lumL_085_min,
                                                                                    lumL_085_max, lumL_05_min,
                                                                                    lumL_05_max]))

        max_gain = max(resdict['solution']['netLGain'])
        n_up = 9  # GET from DB or from Job def.
        best1 = best2 = best3 = 0.0
        trans1 = trans2 = trans3 = 0.0
        pdict = {}
        try:
    
            n_cols = resdict['model']['icSet'][0].from_dim
            #n_lines = resdict['model']['icSet'][0].to_dim
            energies = resdict['model']['cellBasis0']['spectrum']['energies']
            # calculer Dij=Ej-Ei
            Dij = []
            for i in range(len(energies)):
                temp = []
                for j in range(len(energies)):
                    temp.append(energies[j]-energies[i])
                Dij.append(temp)
            good_k = []
            for k in range(len(Dij)):
                if Dij[k][n_up]>0:
                    good_k.append(k)
            # k where E_k,nup>0:
            #self.log.info('Good k values:', good_k)
            dipoles_array = []
            t_v = []
            for i in range(len(resdict['model']['icDipoles'][0])):
                t_v.append(resdict['model']['icDipoles'][0][i])
                if (i+1) % n_cols == 0:
                    dipoles_array.append(t_v)
                    t_v = []
            upper_vals = dipoles_array[n_up]
            v_dict = []
            for i in good_k:
                v_dict.append((abs(upper_vals[i]), i))
            copy_sorted = sorted(v_dict)
            best1 = copy_sorted[-1][0]
            best2 = copy_sorted[-2][0]
            best3 = copy_sorted[-3][0]
            self.log.info( "Best dipoles, sorted:", [best1, best2, best3])
            best1_j = copy_sorted[-1][1]
            best2_j = copy_sorted[-2][1]
            best3_j = copy_sorted[-3][1]
            pdict["dipole1"] = best1
            pdict["dipole2"] = best2
            pdict["dipole3"] = best3
            self.log.info("Indices for best dipoles:", [best1_j, best2_j, best3_j])
            
            ##Buggy, so removed for the time being
            #trans_array = []
            #t_v = []
            #for i in range(len(resdict['model']['icEtrans'][0])):
            #    t_v.append(resdict['model']['icEtrans'][0][i])
            #    if (i+1)%n_cols ==0:
            #        trans_array.append(t_v)
            #        t_v = []
            #upper_trans = trans_array[n_up]
            
            #trans1 = upper_trans[best1_j]
            #trans2 = upper_trans[best2_j]
            #trans3 = upper_trans[best3_j]
            #self.log.info("Transition Energy, sorted:", [trans1, trans2, trans3])
            
            self.log.info("Transition Energy, sorted:", 
                          ' '.join([Dij[best1_j][n_up], Dij[best2_j][n_up], Dij[best3_j][n_up]]))
            pdict['trans1'] = Dij[best1_j][n_up]
            pdict['trans2'] = Dij[best2_j][n_up]
            pdict['trans3'] = Dij[best3_j][n_up]
            
        except Exception as error:
            self.log.error("Failed to read the dipoles and the Transition energies", error)
        
        pdict['current'] = resdict['solution']['netCurrent']
        pdict['photon_energy'] = resdict['solution']["Photon_Energy"]
        pdict['photon_flux'] = resdict['solution']["Photon_Flux"]
        pdict['max_gain'] = max_gain
        
        if self.store_output:
            self.log.info("Sending results to DB")
            if not self.debug:
                self.log.info("Sending %s" % str(pdict))
                res = self.simudb.setAnalysisParameters(self.taskname, pdict)
                if not res['OK']:
                    if 'rpcStub' in res:
                        failover = _sendToFailover(res['rpcStub'], self.taskname)
                        if not failover['OK']:
                            self.log.error('Failed failover', failover['Message'])
                            self.log.error('Issue with registration', res['Message'])
                            return S_ERROR("Issue when registering.")
                    else:
                        self.log.error('Bad RPC query, issue when registering', res['Message'])
                        return S_ERROR("Failed to register analysis parameters")
            else:
                self.log.info("Would have tried to send the results")
        else:
            self.log.info("This job shouldn't store its output to the DB")
        return S_OK()


def _sendToFailover( rpcStub, jobname):
    """ Create a ForwardDISET operation for failover
    """
    request = Request()
    request.RequestName = "Analysis.%s" % (jobname)
    forwardDISETOp = Operation()
    forwardDISETOp.Type = "ForwardDISET"
    forwardDISETOp.Arguments = DEncode.encode(rpcStub)
    request.addOperation(forwardDISETOp)
    
    return ReqClient().putRequest(request)

