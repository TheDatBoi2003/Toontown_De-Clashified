from toontown.suit import DistributedFactorySuitAI
from direct.directnotify import DirectNotifyGlobal

class DistributedMintSuitAI(DistributedFactorySuitAI.DistributedFactorySuitAI):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedMintSuitAI')

    def isSupervisor(self):
        return self.boss and self.track == 'm'

    def isPresident(self):
        return self.boss and self.track == 'c'
