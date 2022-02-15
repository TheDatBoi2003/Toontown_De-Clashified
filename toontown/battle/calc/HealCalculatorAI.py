from math import ceil

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

    def calcAttackResults(self, attack, toonId):
        _, atkLevel, atkHp = getActualTrackLevelHp(attack)
        targetList = createToonTargetList(self.battle, toonId)
        toon = self.battle.getToon(toonId)
        healing = doDamageCalc(atkLevel, HEAL, toon)
        prestige, propBonus = getToonPrestige(self.battle, toonId, HEAL), getToonPropBonus(self.battle, HEAL)
        if not attackHasHit(attack, suit=0):
            healing *= 0.2
        self.notify.debug('toon does ' + str(healing) + ' healing to toon(s)')

        toons = self.battle.activeToons
        if prestige or propBonus:
            if not (prestige and propBonus) or not PropAndPrestigeStack:
                healAmt = int(ceil(healing * 0.5))
            else:
                healAmt = healing
            attack[TOON_HP_COL][toons.index(toon)] = healAmt
            self.notify.debug('Prestige Bonus: toon does %d self-healing' % healAmt)

        healing /= len(targetList)
        self.notify.debug('Splitting heal among targets')

        results = [0 for _ in xrange(len(toons))]
        healedToons = 0
        for target in targetList:

            healedToons += self.getToonHp(target) > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, healing))

            if target not in toons:
                self.notify.debug("The toon is not accessible!")
                continue

            results[toons.index(target)] = healing
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return healedToons > 0

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
