from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *
from toontown.toonbase.ToontownBattleGlobals import AvProps
from toontown.battle.ToonBattleGlobals import *


class LureCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('LureCalculatorAI')

    def __init__(self, battle, statusCalculator, trapCalculator):
        DirectObject.__init__(self)
        self.luredSuits = []                        # Keeps track of suit lured over a longer period of time
        self.successfulLures = set()                   # Keeps track of successful lures for the current turn
        self.delayedWakes = set()                      # Store cogs that will lose the lure status at the end of the turn
        self.battle = battle
        self.statusCalculator = statusCalculator
        self.trapCalculator = trapCalculator
        self.accept('init-round', self.__resetFields)
        self.accept('delayed-wake', self.__addSuitToDelayedWake)
        self.accept('lured-hit-exp', self.__calcLuredHitExp)
        self.accept('post-toon', self.__postToonStatusRounds)
        self.accept('update-active-toons', self.__updateActiveToons)

    def cleanup(self):
        self.ignoreAll()

    def calcAttackResults(self, attack, toonId):
        atkLevel = attack[TOON_LVL_COL]
        targetList = createToonTargetList(self.battle, toonId)
        suits = self.battle.activeSuits
        results = [0 for _ in xrange(len(suits))]
        numLured = 0
        for target in targetList:
            result = LURE_SUCCEEDED
            targetLured, validTarget = self.lureSuit(atkLevel, attack, target, toonId)
            suitId = target.getDoId()
            if self.trapCalculator.getSuitTrapType(target) != NO_TRAP:
                attackDamage, trapLevel, trapCreatorId = self.trapCalculator.getTrapInfo(target)
                if trapCreatorId > 0:
                    self.notify.debug('Giving trap EXP to toon ' + str(trapCreatorId))
                    messenger.send('add-exp', [attack, TRAP_TRACK, trapLevel, trapCreatorId])
                self.trapCalculator.clearTrapCreator(trapCreatorId, target)
                self.notify.debug('Suit lured right onto a trap! (%s,%s)' %
                                  (AvProps[TRAP][trapLevel], trapLevel))
                result = attackDamage
                self.trapCalculator.removeTrapStatus(target)
            if targetLured and suitId not in self.successfulLures:
                self.successfulLures.add(suitId)
                tgtPos = self.battle.activeSuits.index(target)
                if target in self.trapCalculator.trappedSuits:
                    self.trapCalculator.removeTrapStatus(target)
                attack[TOON_KBBONUS_COL][tgtPos] = KB_BONUS_TGT_LURED
                attack[TOON_HP_COL][tgtPos] = result

            numLured += validTarget

            if result != 0:
                if target not in suits:
                    self.notify.debug("The suit is not accessible!")
                    continue

                if result > 0 and target in self.luredSuits:
                    messenger.send('lured-hit-exp', [attack, target])

                results[suits.index(target)] = result
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return numLured > 0

    def lureSuit(self, atkLevel, attack, target, toonId):
        targetLured = 0
        validTarget = 0
        if not target.getStatus(LURED_STATUS):
            validTarget = target.getHP() > 0
            if attack[TOON_TRACK_COL] == NPCSOS:
                self.addLureStatus(target, atkLevel)
            else:
                self.addLureStatus(target, atkLevel, toonId)
                toon=simbase.air.doId2do.get(toonId)
                self.addLureStatusTest(toon, atkLevel, toonId)
            targetLured = 1
        return targetLured, validTarget

    def addLureStatusTest(self, toon, atkLevel, toonId=-1):
        lureStatus = genToonStatus(TEST_STATUS)
        lureStatus['levels'] = 1
        toon.b_addStatus(lureStatus)
        self.notify.debug('Toon %s now has a %s status effect!.' % (toon.doId, lureStatus['levels']))

    def addLureStatus(self, suit, atkLevel, toonId=-1):
        lureStatus = genSuitStatus(LURED_STATUS)
        rounds = NumRoundsLured[atkLevel]
        lureStatus['rounds'] = rounds
        lureStatus['toons'].append(toonId)
        lureStatus['levels'].append(atkLevel)
        if getToonPrestige(self.battle, toonId, LURE_TRACK):
            lureStatus['decay'] = 105
            lureStatus['kbBonus'] = 0.65
        suit.b_addStatus(lureStatus)
        self.notify.debug('%s now has a level %d lure for %d rounds.' % (suit.doId, atkLevel, rounds))
        self.luredSuits.append(suit)
        messenger.send('lure-suit', [self.luredSuits, suit])

    def wakeSuitFromAttack(self, calc, toonId):
        targetList = createToonTargetList(self.battle, toonId)
        for target in targetList:
            luredStatus = target.getStatus(LURED_STATUS)
            if luredStatus and calc.bonusExists(target, hp=0):
                self.removeLureStatus(target, luredStatus)
                self.notify.debug('Suit %d stepping from lured spot' % target.getDoId())
            else:
                self.notify.debug('Suit ' + str(target.doId) + ' not found in currently lured suits')

    def wakeDelayedLures(self):
        for target in self.delayedWakes:
            if not target:
                continue
            luredStatus = target.getStatus(LURED_STATUS)
            if luredStatus:
                self.removeLureStatus(target, luredStatus)
                self.notify.debug('Suit %d will be stepping back from lured spot' % target.doId)
            else:
                self.notify.debug('Suit ' + str(target.doId) + ' not found in currently lured suits')

        self.delayedWakes = set()

    def removeLureStatus(self, suit, statusRemoved=None):
        if suit in self.luredSuits:
            self.luredSuits.remove(suit)
            if statusRemoved:
                self.statusCalculator.removeStatus(suit, statusRemoved)
            else:
                self.statusCalculator.removeStatus(suit, statusName=LURED_STATUS)

    @staticmethod
    def __getLuredExpInfo(suit):
        returnInfo = []
        lureStatus = suit.getStatus(LURED_STATUS)
        lureToons = lureStatus['toons']
        lureLevels = lureStatus['levels']
        if len(lureToons) == 0:
            return returnInfo
        for i in xrange(len(lureToons)):
            if lureToons[i] != -1:
                returnInfo.append([lureToons[i], lureLevels[i]])

        return returnInfo

    def __resetFields(self):
        self.successfulLures = set()

    def __addSuitToDelayedWake(self, toonId, target=None, ignoreDamageCheck=False):
        if target:
            self.delayedWakes.add(target)
        else:
            targetList = createToonTargetList(self.battle, toonId)
            for thisTarget in targetList:
                attack = self.battle.toonAttacks[toonId]
                pos = self.battle.activeSuits.index(thisTarget)
                if (thisTarget.getStatus(LURED_STATUS) and target not in self.delayedWakes and
                        (attack[TOON_HP_COL][pos] > 0 or ignoreDamageCheck)):
                    self.delayedWakes.add(target)

    def __calcLuredHitExp(self, attack, target):
        for (toonId, level) in self.__getLuredExpInfo(target):
            if toonId > 0:
                self.notify.debug('Giving lure EXP to toon %d' % toonId)
                messenger.send('add-exp', [attack, LURE_TRACK, level, toonId])

    def __postToonStatusRounds(self):
        for suit in self.battle.activeSuits:
            removedStatus = suit.decStatusRounds(LURED_STATUS)
            if removedStatus:
                self.removeLureStatus(suit, removedStatus)
            else:
                # activeSuit.getStatus(LURED_STATUS)['decay'] -= 5 # This is lure decay in action
                pass

    def __updateActiveToons(self):
        for suit in self.luredSuits:
            lureStatus = suit.getStatus(LURED_STATUS)
            for toon in lureStatus['toons']:
                if toon != -1 and toon not in self.battle.activeToons:
                    toonIndex = lureStatus['toons'].index(toon)
                    self.notify.debug('Lure for ' + str(toon) + ' will no longer give exp')
                    lureStatus['toons'][toonIndex] = -1
