from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from StatusEffectResponderAI import *
from toontown.battle.calc.BattleCalculatorGlobals import *


class StatusEffectManagerAI(DirectObject):
    
    def __init__(self, av):
        self.av = av
        self.statusEffectResponders = {}
    
    def addStatusEffectResponder(self, statusBaser, statusName, statusValue, statusRounds, statusInfinite, statusExtraArgs):
        self.statusEffectResponders[statusName] = StatusEffectResponderAI(self.av, statusBaser, statusName, statusValue, statusRounds, statusInfinite, statusExtraArgs)
        self.statusEffectResponders[statusName].applyStatus()
    
    def addStatusEffectResponderFromDict(self, statusDictName):
        self.addStatusEffectResponder(statusDictName[STATUS_EFFECT_BASER],
                                      statusDictName[STATUS_EFFECT_NAME],
                                      statusDictName[STATUS_EFFECT_VALUE],
                                      statusDictName[STATUS_EFFECT_ROUNDS],
                                      statusDictName[STATUS_EFFECT_INFINITE],
                                      statusDictName[STATUS_EFFECT_EXTRA_ARGS])
    
    def removeStatusEffectResponder(self, statusName):
        self.statusEffectResponders[statusName].removeStatus()
        del self.statusEffectResponders[statusName]
    
    def calculateStatusEffects(self):
        for statusEffectResponder in self.statusEffectResponders.values():
            statusEffectResponder.removeRound()
            if statusEffectResponder.getRounds() <= 0 and not statusEffectResponder.infinite:
                self.removeStatusEffectResponder(statusEffectResponder.getStatusName())