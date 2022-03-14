"""Electric vehicle charging rate control"""

from andes.core.param import NumParam
from andes.core.var import Algeb
from andes.core.discrete import Limiter, DeadBand

from andes.models.distributed.ev import EV2Data, EV2Model


class EVControlData(EV2Data):
    """
    Data for EV charging rate control
    """
    def __init__(self):
        EV2Data.__init__(self)
        self.chargerv = NumParam(default=400.0, info='Rated voltage of EV charger', #May be unnecessary to include?
                            tex_name='v_{charger}',
                            unit='V',
                            )
        #Replace Icmin and Icmax with power min/max.
        self.Pcmin = NumParam(default=0.0, info='Minimum charging power',
                            tex_name='P_{c,min}',
                            unit='MW',
                            )
        self.Pcmax = NumParam(default=69.0, info='Maximum charging current', #Will change depending on SOC of cluster
                            tex_name='P_{c,max}',
                            unit='MW',
                            )
        self.FThresMax = NumParam(default=60.6, info='Frequency threshold maxmimum to trigger charge control participation',
                            tex_name='f_{threshold,max}',
                            unit='Hz',
                            )
        self.FThresMin = NumParam(default=59.4, info='Frequency threshold minimum to trigger charge control participation',
                            tex_name='f_{threshold,min}',
                            unit='Hz',
                            )
        self.NumEV = NumParam(default=100,
                             info='Number of EVs connected to the system within the same SOC range',
                             tex_name='NumEV',
                             )                            
        self.pratio = NumParam(default=-0.75,
                             info='Initial charging power ratio multiplied to pmx in [-1, 1]',
                             tex_name='p_{ratio}',
                             vrange=(-1, 1),
                             )
        self.FDevMax = NumParam(default=5.0,
                             info='Maximum frequency deviation from 60Hz that EVs will alter charging power to support',
                             tex_name='freq_{dev,max}',
                             unit='Hz',
                             )
        self.tsteady = NumParam(default=2.0, info='Length of time that frequency stays within threshold frequency to turn charge control off',
                            tex_name='t_{steady}',
                            unit='s',
                            )

class EVControlModel(EV2Model):
    """
    Model implementation of EV charge control
    """
    def __init__(self, system, config):
        EV2Model.__init__(self, system, config)

        #Set nominal charging power
        self.Pcnom = Algeb(info='Nominal charging power',
                           v_str='(Pcmax - Pcmin)*Pratio',
                           e_str='(Pcmax - Pcmin)*Pratio-Pcnom',
                           tex_name='P_{c,nom}'
                           )

        #Set total charging power of each cluster
        self.Pcluster = Algeb(info='Charging power of each EV cluster',
                           v_str='Pcnom*NumEV',
                           e_str='Pcnom*NumEV - Pcluster',
                           tex_name='P_{cluster}'
                           )
        
        #If freqdev is larger than freqtheshold (0.6Hz for now), apply power change. 
        self.freqDev = Algeb(info='COI Frequency deviation from 60Hz',
                             v_str='COI - 60',
                             e_str='COI - 60 - freqDev',
                            )
                            
        self.freqDB = DeadBand(u=self.freqDev, center=60, lower=self.FThresMin,
                            upper=self.FThresMax, tex_name='FreqDB',
                            info='Deadband for COI speed',
                            )
        
        #Define charge control equation based on freqDB
        self.Pnew = Algeb(info='Charging power after comparing COI frequency deviation to 60Hz',#Should this be self.Pe?
                          v_str='(Pcluster + (freqDev/FDevMax)*(Pcmax*NumEV - Pcluster))*freqDB_zl - (freqDev/FDevMax)*(Pcmax*NumEV - Pcluster)*freqDB_zu',
                          e_str='(Pcluster + (freqDev/FDevMax)*(Pcmax*NumEV - Pcluster))*freqDB_zl - (freqDev/FDevMax)*(Pcmax*NumEV - Pcluster)*freqDB_zu - Pnew'
        )

        