'''
Created on Mar 5, 2014

@author: stephanep
'''
from DIRAC.Core.Base.Client import Client
from DIRAC.Core.Utilities.ReturnValues import S_OK
from DIRAC.Core.DISET.TransferClient import TransferClient
import os

class SimuDBClient(Client):
    """ Client classs for the SimuDBHandler
    """
    def __init__( self, **kwargs ):

        Client.__init__( self, **kwargs )
        self.setServer( 'SimuDB/SimuDB' )
        self.tranferclient = TransferClient(self.getServer())
        
    def sendResult(self, file_path):
        """ Send the result
        """
        return self.tranferclient.sendFile(file_path, os.path.basename(file_path))
