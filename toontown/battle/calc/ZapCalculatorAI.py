from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *
from toontown.toonbase.ToontownBattleGlobals import *

MAX_JUMPS = len(AvZapJumps[0])

class ZapCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('SquirtCalculatorAI')

    def __init__(self, battle, squirtCalculator):
        DirectObject.__init__(self)
        self.jumpedSuits = []
        self.battle = battle
        self.squirtCalculator = squirtCalculator
        self.accept('init-round', self.__resetFields)

    def cleanup(self):
        self.ignoreAll()

    def calcZapHit(self, attackIndex, target, currAtk, prevAttack, prevAtkTrack):
        if target in self.squirtCalculator.soakedSuits:
            return 0

        attack = self.battle.toonAttacks[attackIndex]
        atkTrack, atkLevel = getActualTrackLevel(attack, self.notify)

        if currAtk > 0:
            if atkTrack == prevAtkTrack and attack[TOON_TGT_COL] == prevAttack[TOON_TGT_COL]:
                if prevAttack[TOON_MISSED_COL]:
                    self.notify.debug('DODGE: Toon attack track dodged')
                else:
                    self.notify.debug('HIT: Toon attack track hit')
                return prevAttack[TOON_MISSED_COL]

        acc = AvPropAccuracy[atkTrack][atkLevel]

        lureStatus = target.getStatus(LURED_STATUS)
        if lureStatus:
            acc = max(acc, lureStatus['decay'])

        if attack[TOON_TRACK_COL] == NPCSOS:
            randChoice = 0
        else:
            randChoice = random.randint(0, 99)

        if randChoice < acc:
            self.notify.debug('HIT: Toon attack rolled' + str(randChoice) + 'to hit with an accuracy of' + str(acc))
            return 0
        else:
            self.notify.debug('MISS: Toon attack rolled' + str(randChoice) + 'to hit with an accuracy of' + str(acc))
            return 1

    def calcAttackResults(self, attack, targets, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack, self.notify)
        toon = self.battle.getToon(toonId)
        npcSOS = attack[TOON_TRACK_COL] == NPCSOS
        attack[TOON_HPBONUS_COL] = [-1 for _ in xrange(len(targets))]
        targetList = self.__calcJumpPositions(toonId)
        targetsHit = 0

        prestige = toon.checkTrackPrestige(ZAP)
        propBonus = getToonPropBonus(self.battle, ZAP)
        if PropAndPrestigeStack and prestige and propBonus:
            soakBonuses = AvZapJumps[2]
        elif prestige or propBonus:
            soakBonuses = AvZapJumps[1]
        else:
            soakBonuses = AvZapJumps[0]

        for i in xrange(len(targetList)):
            target = targetList[i]

            if target not in targets:
                self.notify.debug("The suit is not accessible!")
                continue

            tgtPos = self.battle.activeSuits.index(target)
            attack[TOON_HPBONUS_COL][tgtPos] = i

            baseDamage = doInstaKillCalc(self.battle, atkHp, atkLevel, atkTrack, npcSOS,
                                         target, toon, PropAndPrestigeStack)

            targetsHit += target.getHP() > 0

            if target.getStatus(LURED_STATUS):
                self.notify.debug('Zap on lured suit, indicating with KB_BONUS_COL flag')
                attack[TOON_KBBONUS_COL][tgtPos] = KB_BONUS_LURED_FLAG
                messenger.send('delayed-wake', [toonId, target])
                messenger.send('lured-hit-exp', [attack, target])

            if target in self.squirtCalculator.soakedSuits:
                attackDamage = int(math.ceil(baseDamage * soakBonuses[i]))  # <--------  THIS IS THE ATTACK OUTPUT!
            else:
                attackDamage = baseDamage  # <--------  THIS IS THE ATTACK OUTPUT!

            self.notify.debug('%d targets %s, damage: %d' % (toonId, target, attackDamage))
            messenger.send('soaked-suit-zap', [attack, target])

            attack[TOON_HP_COL][tgtPos] = attackDamage
        return targetsHit

    def __calcJumpPositions(self, toonId):
        attack = self.battle.toonAttacks[toonId]
        atkTrack, atkLevel = getActualTrackLevel(attack, self.notify)
        targetList = []
        if atkTrack == NPCSOS:
            return self.battle.activeSuits

        firstSuit = self.battle.findSuit(attack[TOON_TGT_COL])
        if firstSuit:
            targetList.append(firstSuit)
            if firstSuit in self.squirtCalculator.soakedSuits:
                lastIndex = firstIndex = self.battle.activeSuits.index(firstSuit)
                for _ in xrange(1, MAX_JUMPS):
                    nextSuit = self.__jumpToLeftSuit(lastIndex, firstIndex)
                    if nextSuit:
                        targetList.append(nextSuit)
                        lastIndex = self.battle.activeSuits.index(nextSuit)
                        self.jumpedSuits[lastIndex] = True
                        continue
                    nextSuit = self.__jumpToRightSuit(lastIndex, firstIndex)
                    if nextSuit:
                        targetList.append(nextSuit)
                        lastIndex = self.battle.activeSuits.index(nextSuit)
                        self.jumpedSuits[lastIndex] = True
                        continue

        return targetList

    def __jumpToRightSuit(self, targetIndex, firstIndex):
        if targetIndex > 0 and self.battle.activeSuits[targetIndex - 1] in self.squirtCalculator.soakedSuits \
                and self.battle.activeSuits[targetIndex - 1].getHP() > 0:
            if not self.jumpedSuits[targetIndex - 1] and targetIndex - 1 != firstIndex:
                return self.battle.activeSuits[targetIndex - 1]
        if targetIndex > 1 and self.battle.activeSuits[targetIndex - 2] in self.squirtCalculator.soakedSuits \
                and self.battle.activeSuits[targetIndex - 2].getHP() > 0:
            if not self.jumpedSuits[targetIndex - 2] and targetIndex - 2 != firstIndex:
                return self.battle.activeSuits[targetIndex - 2]
        return None

    def __jumpToLeftSuit(self, targetIndex, firstIndex):
        numSuits = len(self.battle.activeSuits) - 1
        if targetIndex < numSuits and self.battle.activeSuits[targetIndex + 1] in self.squirtCalculator.soakedSuits \
                and self.battle.activeSuits[targetIndex + 1].getHP() > 0:
            if not self.jumpedSuits[targetIndex + 1] and targetIndex + 1 != firstIndex:
                return self.battle.activeSuits[targetIndex + 1]
        if targetIndex < numSuits-1 and self.battle.activeSuits[targetIndex + 2] in self.squirtCalculator.soakedSuits \
                and self.battle.activeSuits[targetIndex + 2].getHP() > 0:
            if not self.jumpedSuits[targetIndex + 2] and targetIndex + 2 != firstIndex:
                return self.battle.activeSuits[targetIndex + 2]
        return None

    def __resetFields(self):
        self.jumpedSuits = [False for _ in xrange(len(self.battle.activeSuits))]
