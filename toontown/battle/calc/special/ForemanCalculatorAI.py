import math

from toontown.battle.SuitBattleGlobals import *
from toontown.battle.calc.BattleCalculatorGlobals import APPLY_HEALTH_ADJUSTMENTS
from toontown.battle.calc.SuitCalculatorAI import SuitCalculatorAI


class ForemanCalculatorAI(SuitCalculatorAI):
    notify = DirectNotifyGlobal.directNotify.newCategory('ForemanCalculatorAI')

    def __init__(self, battle, suit, healCalculator):
        SuitCalculatorAI.__init__(self, battle, suit, healCalculator)
        self.suit.hardMaxHP = 1.75
        self.attackPower = 1.0
        self.accept('suit-killed', self.__compensate)

    def __compensate(self, suit):
        self.suit.setHP(self.suit.getHP() + self.suit.getMaxHP() * 0.25)
        self.attackPower *= 1.15

    def __applySuitAttackDamages(self, attackIndex):
        attack = self.battle.suitAttacks[attackIndex]
        attack = math.ceil(attack * self.attackPower)
        if APPLY_HEALTH_ADJUSTMENTS:
            for toon in self.battle.activeToons:
                self.healCalculator.hurtToon(attack, toon)
