from direct.showbase.MessengerGlobal import messenger

from StatusCalculatorAI import *
from toontown.battle.calc.BattleCalculatorGlobals import *


class SquirtCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('SquirtCalculatorAI')

    def __init__(self, battle, statusCalculator):
        DirectObject.__init__(self)
        self.soakedSuits = []                       # Keeps track of soaked suits over a longer period of time
        self.battle = battle
        self.statusCalculator = statusCalculator
        self.accept('post-suit', self.postSuitStatusRounds)

    def cleanup(self):
        self.ignoreAll()

    def calcAttackResults(self, attack, targets, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack, self.notify)
        toon = self.battle.getToon(toonId)
        targetList, suitIndex = self.__calcSquirtTargets(attack, toon)
        npcSOS = attack[TOON_TRACK_COL] == NPCSOS
        results = [0 for _ in xrange(len(targets))]
        targetsExist = 0
        for target in targetList:
            self.soakSuit(atkLevel, target)
            attackDamage = 0
            if targets[suitIndex] == target:
                attackDamage = doInstaKillCalc(self.battle, atkHp, atkLevel, atkTrack, npcSOS, target,
                                               toon, PropAndPrestigeStack)
                self.notify.debug('%d targets %s, damage: %d' % (toonId, target, attackDamage))
            elif self.notify.getDebug():
                self.notify.debug('%d targets %s to soak' % (toonId, target))

            targetsExist += target.getHP() > 0

            if target not in targets:
                self.notify.debug("The suit is not accessible!")
                continue

            if attackDamage > 0 and target.getStatus(LURED_STATUS):
                messenger.send('lured-hit-exp', [attack, target])

            results[targets.index(target)] = attackDamage
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsExist > 0

    def soakSuit(self, atkLevel, suit):
        soakStatus = suit.getStatus(SOAKED_STATUS)
        soakRounds = NumRoundsSoaked[atkLevel]
        if not soakStatus or soakStatus['rounds'] < soakRounds:
            if soakStatus:
                self.statusCalculator.removeStatus(suit, soakStatus)
            self.addSoakStatus(suit, soakRounds)

    def addSoakStatus(self, suit, rounds):
        soakStatus = genSuitStatus(SOAKED_STATUS)
        soakStatus['rounds'] = rounds
        suit.b_addStatus(soakStatus)
        self.notify.debug('%s now is soaked for %d rounds.' % (suit.doId, rounds))
        self.soakedSuits.append(suit)
        messenger.send('soak-suit', [self.soakedSuits, suit])

    def removeSoakStatus(self, suit, statusRemoved=None):
        if suit in self.soakedSuits:
            self.soakedSuits.remove(suit)
            if statusRemoved:
                self.statusCalculator.removeStatus(suit, statusRemoved)
            else:
                self.statusCalculator.removeStatus(suit, statusName=SOAKED_STATUS)

    def postSuitStatusRounds(self):
        for activeSuit in self.battle.activeSuits:
            removedStatus = activeSuit.decStatusRounds(SOAKED_STATUS)
            if removedStatus:
                self.removeSoakStatus(activeSuit, removedStatus)

    def __calcSquirtTargets(self, attack, toon):
        targets = []
        target = self.battle.findSuit(attack[TOON_TGT_COL])
        targets.append(target)
        activeSuits = self.battle.activeSuits
        suitIndex = activeSuits.index(target)
        if toon.checkTrackPrestige(SQUIRT):
            if suitIndex - 1 >= 0:
                targets.append(activeSuits[suitIndex - 1])
            if suitIndex + 1 < len(activeSuits):
                targets.append(activeSuits[suitIndex + 1])
        return targets, suitIndex
