from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *


class SuitCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('SuitCalculatorAI')
    suitsAlwaysHit = simbase.config.GetBool('suits-always-hit', 0)
    suitsAlwaysMiss = simbase.config.GetBool('suits-always-miss', 0)

    def __init__(self, battle, suit, healCalculator):
        DirectObject.__init__(self)
        self.battle = battle
        self.suit = suit
        self.healCalculator = healCalculator
        self.attackers = {}
        self.attack = None
        self.suitAtkStats = {}
        self.accept('init-round', self.__clearAttackers)
        self.accept('toon-threat', self.rememberToonAttack)

    def cleanup(self):
        self.ignoreAll()

    def calcSuitAttack(self):
        suitIndex = self.battle.activeSuits.index(self.suit)
        self.attack = self.battle.suitAttacks[suitIndex]
        if self.suit in self.battle.activeSuits:
            suitId = self.suit.doId
            self.attack[SUIT_ID_COL] = suitId
            if not self.__suitCanAttack():
                self.notify.debug("Suit %d can't attack" % suitId)
                return
            if self.battle.pendingSuits.count(self.suit) > 0 or self.battle.joiningSuits.count(self.suit) > 0:
                return
            self.attack[SUIT_ID_COL] = self.battle.activeSuits[suitIndex].doId
            self.attack[SUIT_ATK_COL] = self.__calcSuitAtkType()
            self.attack[SUIT_TGT_COL] = self.__calcSuitTarget()
            if self.attack[SUIT_TGT_COL] == -1:
                self.attack = getDefaultSuitAttack()
                self.notify.debug('clearing suit attack, no avail targets')
            self.__calcSuitAtkHp()
            if self.attack[SUIT_ATK_COL] != NO_ATTACK:
                if self.__suitAtkAffectsGroup(self.attack):
                    for currTgt in self.battle.activeToons:
                        self.__updateSuitAtkStat(currTgt)

                else:
                    tgtId = self.battle.activeToons[self.attack[SUIT_TGT_COL]]
                    self.__updateSuitAtkStat(tgtId)
            targets = self.__createSuitTargetList()
            allTargetsDead = 1
            for currTgt in targets:
                if self.healCalculator.getToonHp(currTgt) > 0:
                    allTargetsDead = 0
                    break

            if allTargetsDead:
                self.attack = getDefaultSuitAttack()
                if self.notify.getDebug():
                    self.notify.debug('clearing suit attack, targets dead')
                    self.notify.debug('suit attack is now ' + repr(self.attack))
                    self.notify.debug('all attacks: ' + repr(self.battle.suitAttacks))
            if attackHasHit(self.attack, suit=1):
                self.__applySuitAttackDamages(suitIndex)
            if self.notify.getDebug():
                self.notify.debug('Suit attack: ' + str(self.attack))
            self.attack[SUIT_BEFORE_TOONS_COL] = 0

    def rememberToonAttack(self, toonId, damage):
        if not self.attackers:
            self.attackers = {toonId: damage}
        else:
            if toonId not in self.attackers or self.attackers[toonId] <= damage:
                self.attackers[toonId] = damage

    def clearMissingAttackers(self):
        if not CLEAR_SUIT_ATTACKERS:
            for toonId in self.attackers.keys():
                if toonId not in self.battle.activeToons:
                    del self.attackers[toonId]

    def hitSuit(self, attack, damage):
        markedStatus = self.suit.getStatus(MARKED_STATUS)
        if markedStatus and not (markedStatus['rounds'] == 2 and attack[TOON_TRACK_COL] == THROW):
            damage *= 1 + markedStatus['damage-mod']
            attack[TOON_HP_COL][self.battle.activeSuits.index(self.suit)] = damage
        self.suit.setHP(self.suit.getHP() - damage)
        messenger.send('suit-was-hit', [attack, damage])

    def removeAttacker(self, toonId):
        if not CLEAR_SUIT_ATTACKERS:
            if toonId in self.attackers:
                del self.attackers[toonId]

    def removeAttackStats(self, toonId):
        if toonId in self.suitAtkStats:
            del self.suitAtkStats[toonId]

    def __applySuitAttackDamages(self, attackIndex):
        attack = self.battle.suitAttacks[attackIndex]
        if APPLY_HEALTH_ADJUSTMENTS:
            for toon in self.battle.activeToons:
                self.healCalculator.hurtToon(attack, toon)

    def __calcSuitAtkHp(self):
        targetList = self.__createSuitTargetList()
        attack = self.attack
        for currTarget in xrange(len(targetList)):
            toonId = targetList[currTarget]
            toon = self.battle.getToon(toonId)
            result = 0
            if toon and toon.immortalMode:
                result = 1
            elif TOONS_TAKE_NO_DAMAGE:
                result = 0
            elif self.__suitAtkHit():
                atkType = attack[SUIT_ATK_COL]
                atkInfo = SuitBattleGlobals.getSuitAttack(self.suit.dna.name, self.suit.getLevel(), atkType)
                result = int(atkInfo['hp'] +
                             math.ceil(atkInfo['hp'] * SuitBattleGlobals.EXE_DMG_MOD * self.suit.isExecutive))
            targetIndex = self.battle.activeToons.index(toonId)
            attack[SUIT_HP_COL][targetIndex] = result

    def __calcSuitAtkType(self):
        attacks = SuitBattleGlobals.SuitAttributes[self.suit.dna.name]['attacks']
        atk = SuitBattleGlobals.pickSuitAttack(attacks, self.suit.getLevel())
        return atk

    def __calcSuitTarget(self):
        if random.randint(0, 99) < 75:
            totalDamage = 0
            attackerIds = self.attackers.keys()
            for currToon in attackerIds:
                totalDamage += self.attackers[currToon]

            damages = []
            for currToon in attackerIds:
                damages.append(self.attackers[currToon] / totalDamage * 100)

            dmgIdx = SuitBattleGlobals.pickFromFreqList(damages)
            if dmgIdx is not None:
                toonId = attackerIds[dmgIdx]
            elif attackerIds:
                toonId = random.choice(attackerIds)
            else:
                toonId = random.choice(self.battle.activeToons)
            if toonId == -1 or toonId not in self.battle.activeToons:
                return -1
            self.notify.debug('Suit attacking back at toon ' + str(toonId))
            return self.battle.activeToons.index(toonId)
        else:
            return self.__pickRandomToon()

    def __clearAttackers(self):
        if CLEAR_SUIT_ATTACKERS:
            self.attackers = {}

    def __createSuitTargetList(self):
        attack = self.attack
        targetList = []
        if attack[SUIT_ATK_COL] == NO_ATTACK:
            self.notify.debug('No attack, no targets')
            return targetList
        if not self.__suitAtkAffectsGroup(attack):
            targetList.append(self.battle.activeToons[attack[SUIT_TGT_COL]])
            self.notify.debug('Suit attack is single target')
        else:
            self.notify.debug('Suit attack is group target')
            for currToon in self.battle.activeToons:
                self.notify.debug('Suit attack will target toon' + str(currToon))
                targetList.append(currToon)

        return targetList

    def __pickRandomToon(self):
        liveToons = []
        for currToon in self.battle.activeToons:
            if not self.healCalculator.getToonHp(currToon) <= 0:
                liveToons.append(self.battle.activeToons.index(currToon))

        if len(liveToons) == 0:
            self.notify.debug('No targets avail. for suit ' + str(self.suit.getDoId()))
            return -1
        chosen = random.choice(liveToons)
        self.notify.debug('Suit randomly attacking toon ' + str(self.battle.activeToons[chosen]))
        return chosen

    def __suitAtkAffectsGroup(self, attack):
        atkInfo = getSuitAttack(self.suit.dna.name, self.suit.getLevel(), attack[SUIT_ATK_COL])
        return atkInfo['group'] != ATK_TGT_SINGLE

    def __suitAtkHit(self):
        if self.suitsAlwaysHit:
            return 1
        else:
            if self.suitsAlwaysMiss:
                return 0
        atkType = self.attack[SUIT_ATK_COL]
        atkInfo = SuitBattleGlobals.getSuitAttack(self.suit.dna.name, self.suit.getLevel(), atkType)
        atkAcc = atkInfo['acc']
        suitAcc = SuitBattleGlobals.SuitAttributes[self.suit.dna.name]['acc'][self.suit.getLevel()]
        acc = atkAcc
        randChoice = random.randint(0, 99)
        self.notify.debug('Suit attack rolled %s to hit with an accuracy of %s (attackAcc: %s suitAcc: %s)' %
                          (randChoice, acc, atkAcc, suitAcc))
        if randChoice < acc:
            return 1
        return 0

    def __suitCanAttack(self):
        defeated = not self.suit.getHP() > 0
        rounds = getLureRounds(self.suit)
        revived = self.suit.reviveCheckAndClear()
        self.notify.debug('Can %s attack? Defeated: %s LureRounds: %s NewlyRevived: %s' %
                          (self.suit.doId, defeated, rounds, revived))
        if defeated or rounds >= 1 or revived:
            return 0
        return 1

    def __updateSuitAtkStat(self, toonId):
        if toonId in self.suitAtkStats:
            self.suitAtkStats[toonId] += 1
        else:
            self.suitAtkStats[toonId] = 1
