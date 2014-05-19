'''
Created on May 16, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC.Core.Utilities.ReturnValues import S_OK, S_ERROR
from DIRAC import gLogger
import os
import pickle
import sewlabwrapper.utils.sewlab_convert

class Analysis(ModuleBase):
    '''
    Analysis module: extracts info from the file produced by the SewlabPostProcess 
    Send it to the DB if requested by Job.
    '''


    def __init__(self):

        super(Analysis, self).__init__()
        self.log = gLogger.getSubLogger("Analysis")
        self.store_output = False
        self.debug = False
    def applicationSpecificInputs(self):
        if not os.path.exists(self.InputFile[0]):
            return S_ERROR('Missing Input file')
        if self.debug:
            self.log.info("Using debug mode, i.e. do not communicate with SimuDB")
        return S_OK()
    
    def execute(self):
        
        res = self.resolveInputVariables()
        if not res['OK']:
            self.log.error("Error resolving parameters")
            return res
        
        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'], self.stepStatus['OK']))
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

        self.log.info("Lum found: max, 0.85_min, 0.85_max, 0.5_min, 0.5_max:", str([lumL_max, lumL_085_min, lumL_085_max, lumL_05_min, lumL_05_max]))

        n_up = 9 #GET from DB or from Job def.

        n_cols = resdict['model']['icSet'][0].from_dim
        #n_lines = resdict['model']['icSet'][0].to_dim
        dipoles_array = []
        t_v = []
        for i in range(len(resdict['model']['icDipoles'][0])):
            t_v.append(resdict['model']['icDipoles'][0][i])
            if (i+1)%n_cols == 0:
                dipoles_array.append(t_v)
                t_v = []
        upper_vals = dipoles_array[n_up]
        v_dict = []
        for i in range(len(upper_vals)):
            v_dict.append((abs(upper_vals[i]),i))
        copy_sorted = sorted(v_dict)
        best1 = copy_sorted[-1][0]
        best2 = copy_sorted[-2][0]
        best3 = copy_sorted[-3][0]
        self.log.info( "Best dipoles, sorted:", [best1, best2, best3])
        best1_j = copy_sorted[-1][1]
        best2_j = copy_sorted[-2][1]
        best3_j = copy_sorted[-3][1]
        
        self.log.info("Indices for best dipoles:", [best1_j, best2_j, best3_j])
        
        trans_array = []
        t_v = []
        for i in range(len(resdict['model']['icEtrans'][0])):
            t_v.append(resdict['model']['icEtrans'][0][i])
            if (i+1)%n_cols ==0:
                trans_array.append(t_v)
                t_v = []
        upper_trans = trans_array[n_up]
        
        trans1 = upper_trans[best1_j]
        trans2 = upper_trans[best2_j]
        trans3 = upper_trans[best3_j]
        
        self.log.info("Transition Energy, sorted:", [trans1, trans2, trans3])
        
        if self.store_output:
            self.log.info("Sending results to DB")
            if not self.debug:
                self.log.info("Send")
                ##Do here the sending to DB 
            else:
                self.log.info("Would have tried to send the results")
        else:
            self.log.info("This job shouldn't store its output to the DB")
        return S_OK()