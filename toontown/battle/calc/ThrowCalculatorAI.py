from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *


class ThrowCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('ThrowCalculatorAI')

    def __init__(self, battle, statusCalculator):
        DirectObject.__init__(self)
        self.battle = battle
        self.markedSuits = []                       # Keeps track of marked suits over a longer period of time
        self.statusCalculator = statusCalculator
        self.accept('post-suit', self.__postSuitStatusRounds)

    def cleanup(self):
        self.ignoreAll()

    def calcAttackResults(self, attack, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack)
        targetList = createToonTargetList(self.battle, toonId)
        suits = self.battle.activeSuits
        toon = self.battle.getToon(toonId)
        prestige, propBonus = toon.checkTrackPrestige(atkTrack), getToonPropBonus(self.battle, atkTrack)
        results = [0 for _ in xrange(len(suits))]
        targetsHit = 0
        for target in targetList:
            if target not in suits:
                self.notify.debug("The target is not accessible!")
                continue

            attackDamage = receiveDamageCalc(atkLevel, atkTrack, target, toon)

            targetsHit += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, attackDamage))

            if prestige or propBonus:
                amount = 0.08
                markStatus = target.getStatus(MARKED_STATUS)
                if markStatus:
                    if markStatus['rounds'] > 1:
                        amount = markStatus['damage-mod'] + 0.04
                    self.statusCalculator.removeStatus(target, markStatus)
                if PropAndPrestigeStack and prestige and propBonus:
                    amount += 0.04
                self.__addMarkStatus(target, amount)

            if target.getStatus(LURED_STATUS):
                messenger.send('delayed-wake', [toonId, target])
                messenger.send('lured-hit-exp', [attack, target])

            results[suits.index(target)] = attackDamage
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsHit > 0

    def __addMarkStatus(self, suit, amount):
        markStatus = genSuitStatus(SOAKED_STATUS)
        markStatus['damage-mod'] = amount
        suit.b_addStatus(markStatus)
        self.notify.debug('%s now is marked (%f%%) for 2 rounds.' % (suit.doId, amount * 100))
        self.markedSuits.append(suit)
        messenger.send('mark-suit', [self.markedSuits, suit])

    def removeMarkStatus(self, suit, statusRemoved=None):
        if suit in self.markedSuits:
            self.markedSuits.remove(suit)
            if statusRemoved:
                self.statusCalculator.removeStatus(suit, statusRemoved)
            else:
                self.statusCalculator.removeStatus(suit, statusName=MARKED_STATUS)

    def __postSuitStatusRounds(self):
        for activeSuit in self.battle.activeSuits:
            removedStatus = activeSuit.decStatusRounds(MARKED_STATUS)
            if removedStatus:
                self.removeMarkStatus(activeSuit, removedStatus)
