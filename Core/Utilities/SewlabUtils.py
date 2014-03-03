'''
Created on Mar 3, 2014

@author: stephanep
'''
from math import sqrt

class IVLorentianMesh (object):
    
    def __init__(self, alignmentField, ivSampling, upFraction, ivBroadening):
        
        self.upFraction = upFraction
        self.ivBroadening = ivBroadening
        self.alignmentField = alignmentField
        self.ivSampling = ivSampling
        
        self.electricFields = self._getLorentzMesh(alignmentField, ivSampling)
        
    
    def _getLorentzMesh(self, alignmentField, ivSampling):
        
        highestField = (1.0 + self.upFraction) * alignmentField
        broadeningField = highestField / self.ivBroadening
        
        
        minIntensity = 1.0/(1.0 + pow(highestField/broadeningField, 2.0))
        maxIntensity = 1.0
        
        deltaIntensity = maxIntensity - minIntensity
    
        
        intensities = [minIntensity + i*deltaIntensity/(ivSampling-1) for i in range(ivSampling)]
        electricFields = [self._roundField(highestField - broadeningField * sqrt((1-x)/x)) for x in intensities]
        
        return electricFields
    
    def _roundField(self, field):
        if field < 0.0:
            return 0.0
        else:
            return field
