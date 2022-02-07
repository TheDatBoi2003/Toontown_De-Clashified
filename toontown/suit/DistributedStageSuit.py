from toontown.suit import DistributedFactorySuit
from direct.directnotify import DirectNotifyGlobal

from toontown.toonbase import TTLocalizer


class DistributedStageSuit(DistributedFactorySuit.DistributedFactorySuit):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedStageSuit')

    def setBossName(self):
        self.setName(TTLocalizer.Clerk)
        self.updateName()
