from direct.showbase.DirectObject import DirectObject

from toontown.battle.calc.BattleCalculatorGlobals import *


class HealCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('HealCalculatorAI')

    def __init__(self, battle, statusCalculator):
        DirectObject.__init__(self)
        self.battle = battle
        self.toonHPAdjusts = {}  # Keeps track of healing amount for the current turn
        self.statusCalculator = statusCalculator
        self.accept('init-round', self.__resetFields)
        self.accept('round-over', self.__removeSadToons)

    def cleanup(self):
        self.ignoreAll()

    def calcAttackResults(self, attack, targets, toonId):
        _, atkLevel, atkHp = getActualTrackLevelHp(attack, self.notify)
        targetList = createToonTargetList(self.battle, toonId)
        npcSOS = attack[TOON_TRACK_COL] == NPCSOS
        toon = self.battle.getToon(toonId)
        healing = doDamageCalc(self.battle, atkHp, atkLevel, HEAL, npcSOS, toon, PropAndPrestigeStack)
        if not attackHasHit(attack, self.notify, suit=0):
            healing = healing * 0.2
        self.notify.debug('toon does ' + str(healing) + ' healing to toon(s)')
        healing = healing / len(targetList)
        self.notify.debug('Splitting heal among targets')

        results = [0 for _ in xrange(len(targets))]
        healedToons = 0
        for target in targetList:

            result = healing
            healedToons += self.getToonHp(target) > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, result))

            if target not in targets:
                self.notify.debug("The toon is not accessible!")
                continue

            results[targets.index(target)] = result
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return healedToons

    def healToon(self, toon, attack, healing, position):
        if CAP_HEALS:
            toonHp = self.getToonHp(toon)
            toonMaxHp = self.getToonMaxHp(toon)
            if toonHp + healing > toonMaxHp:
                healing = toonMaxHp - toonHp
                attack[TOON_HP_COL][position] = healing
        self.toonHPAdjusts[toon] += healing
        return healing

    def hurtToon(self, attack, toon):
        position = self.battle.activeToons.index(toon)
        if attack[SUIT_HP_COL][position] <= 0:
            return
        toonHp = self.getToonHp(toon)
        if toonHp - attack[SUIT_HP_COL][position] <= 0:
            self.notify.debug('Toon %d has died, removing' % toon)
            self.battle.__removeToon(toon)
            attack[TOON_DIED_COL] = attack[TOON_DIED_COL] | 1 << position
        self.notify.debug('Toon %s takes %s damage' % (toon, attack[SUIT_HP_COL][position]))
        self.toonHPAdjusts[toon] -= attack[SUIT_HP_COL][position]
        self.notify.debug('Toon %s now has %s health' % (toon, self.getToonHp(toon)))

    def getToonHp(self, toonDoId):
        toon = self.battle.getToon(toonDoId)
        if toon and toonDoId in self.toonHPAdjusts:
            return toon.hp + self.toonHPAdjusts[toonDoId]
        else:
            return 0

    def getToonMaxHp(self, toonDoId):
        toon = self.battle.getToon(toonDoId)
        if toon:
            return toon.maxHp
        else:
            return 0

    def __resetFields(self):
        self.toonHPAdjusts = {}
        for t in self.battle.activeToons:
            self.toonHPAdjusts[t] = 0

    def __removeSadToons(self):
        self.toonHPAdjusts = {}
        for t in self.battle.activeToons:
            self.toonHPAdjusts[t] = 0
