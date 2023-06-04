from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *
from toontown.battle.calc.StatusRepository import *
from toontown.battle.calc.StatusGlobal import *

NextMarks = [0.1, 0.15, 0.18, 0.2]

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
        prestige, propBonus = toon.getTrackPrestige(atkTrack), getToonPropBonus(self.battle, atkTrack)
        results = [0 for _ in xrange(len(suits))]
        targetsHit = 0
        for target in targetList:
            if target not in suits:
                self.notify.debug("The target is not accessible!")
                continue

            attackDamage = receiveDamageCalc(atkLevel, atkTrack, target, toon)

            #addStatusEffectResponder(self, statusBaser, statusName, statusValue, statusRounds, statusInfinite, statusExtraArgs):
            
            target.statusEffectManager.addStatusEffectResponderFromDict(statusRespitory[WORKERS_MANAGEMENT])
            
            targetsHit += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, attackDamage))

            if prestige or propBonus:
                markStatus = target.getStatus(MARKED_STATUS)
                if markStatus:
                    if markStatus['rounds'] > 1:
                        stacks = markStatus['stacks']
                        markBonus = NextMarks[stacks]
                        self.statusCalculator.removeStatus(target, markStatus)
                        self.__addMarkStatus(target, markBonus, stacks=stacks+1)
                else:
                    markBonus = NextMarks[0]
                    if PropAndPrestigeStack and prestige and propBonus:
                        markBonus += 0.03
                    self.__addMarkStatus(target, markBonus)

            if target.getStatus(LURED_STATUS):
                messenger.send('delayed-wake', [toonId, target])
                messenger.send('lured-hit-exp', [attack, target])

            results[suits.index(target)] = attackDamage
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsHit > 0

    def __addMarkStatus(self, suit, markBonus, stacks=1):
        markStatus = genSuitStatus(MARKED_STATUS)
        markStatus['damage-mod'] = markBonus
        markStatus['stacks'] = stacks
        suit.b_addStatus(markStatus)
        self.notify.debug('%s now is marked (%f%%) for 2 rounds.' % (suit.doId, markBonus * 100))
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
