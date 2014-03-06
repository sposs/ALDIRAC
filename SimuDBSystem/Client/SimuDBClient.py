'''
Created on Mar 5, 2014

@author: stephanep
'''
from DIRAC.Core.Base.Client import Client

class SimuDBClient(Client):
    """ Client classs for the SimuDBHandler
    """
    def __init__( self, **kwargs ):

        Client.__init__( self, **kwargs )
        self.setServer( 'SimuDB/SimuDB' )
        