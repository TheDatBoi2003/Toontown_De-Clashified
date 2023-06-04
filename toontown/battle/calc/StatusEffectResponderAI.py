from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger
from StatusEffectFunctionRespitory import *

from toontown.battle.calc.BattleCalculatorGlobals import *


class StatusEffectResponderAI(DirectObject):
    
    def __init__(self, av, statusBaser, statusName, statusValue, statusRounds, statusInfinite, statusExtraArgs):
        self.av = av
        self.statusBaser = statusBaser
        self.statusName = statusName
        self.statusValue = statusValue
        self.rounds = statusRounds
        self.infinite = statusInfinite
        self.extraArgs = statusExtraArgs
    
    def getRounds(self):
        return self.rounds
    
    def removeRound(self):
        self.rounds -= 1
    
    def addRound(self):
        self.rounds += 1
    
    def getAv(self):
        return self.av
    
    def getStatusBaser(self):
        return self.statusBaser
    
    def getStatusName(self):
        return self.statusName
    
    def applyStatus(self):
        getFunctionFromRespitory(self.av, self.statusBaser, self.statusValue)
        
    def removeStatus(self):
        getDoneFunctionFromRespitory(self.av, self.statusBaser, self.statusValue)
        