from toontown.suit import DistributedFactorySuit
from direct.directnotify import DirectNotifyGlobal

from toontown.toonbase import TTLocalizer


class DistributedMintSuit(DistributedFactorySuit.DistributedFactorySuit):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedMintSuit')

    def renameBoss(self):
        self.setName(TTLocalizer.Supervisor)
        self.updateName()
