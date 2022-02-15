from direct.showbase.DirectObject import DirectObject

from toontown.battle.calc.BattleCalculatorGlobals import *


class DropCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('DropCalculatorAI')

    def __init__(self, battle):
        DirectObject.__init__(self)
        self.battle = battle
        self.dropCount = 0
        self.accept('init-round-order', self.__countDrops)

    def cleanup(self):
        self.ignoreAll()

    def calcAccBonus(self, attackId, atkLevel):
        if self.dropCount > 1:
            return
        prestige = getToonPrestige(self.battle, attackId[TOON_ID_COL], DROP)
        propBonus = getToonPropBonus(self.battle, DROP)
        propAcc = AvPropAccuracy[DROP][atkLevel]
        if prestige or propBonus:
            if PropAndPrestigeStack and prestige and propBonus:
                self.notify.debug('using track AND prop bonus accuracy')
                propAcc = (AvBonusAccuracy[DROP][atkLevel] * 2) - AvPropAccuracy[DROP][atkLevel]
            else:
                self.notify.debug('using track OR prop bonus accuracy')
                propAcc = AvBonusAccuracy[DROP][atkLevel]
        return propAcc

    def calcAttackResults(self, attack, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack)
        targetList = createToonTargetList(self.battle, toonId)
        toon = self.battle.getToon(toonId)
        results = [0 for _ in xrange(len(self.battle.activeSuits))]
        targetsHit = 0
        for target in targetList:
            if target not in self.battle.activeSuits:
                self.notify.debug("The target is not accessible!")
                continue

            if target.getStatus(LURED_STATUS):
                attackDamage = 0
                attack[TOON_KBBONUS_COL][self.battle.activeSuits.index(target)] = KB_BONUS_LURED_FLAG
                self.notify.debug('Drop on lured suit! Damage = 0 and setting KB_BONUS_LURED_FLAG')
            else:
                attackDamage = receiveDamageCalc(atkLevel, atkTrack, target, toon)

            targetsHit += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, attackDamage))

            results[self.battle.activeSuits.index(target)] = attackDamage
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsHit > 0

    def __countDrops(self, toonAtkOrder):
        self.dropCount = 0
        for toonAttack in toonAtkOrder:
            if toonAttack in self.battle.toonAttacks and \
                    self.battle.toonAttacks[toonAttack][TOON_TRACK_COL] == DROP:
                self.dropCount += 1
