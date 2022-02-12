from math import ceil

from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *


class SoundCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('TrapCalculatorAI')

    def __init__(self, battle):
        DirectObject.__init__(self)
        self.battle = battle

    def cleanup(self):
        pass

    def calcAttackResults(self, attack, targets, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack, self.notify)
        targetList = createToonTargetList(self.battle, toonId)
        toon = self.battle.getToon(toonId)
        prestige, propBonus = toon.checkTrackPrestige(atkTrack), getToonPropBonus(self.battle, atkTrack)
        results = [0 for _ in xrange(len(targets))]
        targetsHit = 0
        if prestige or propBonus:
            if PropAndPrestigeStack and prestige and propBonus:
                bonusDamage = int(max(target.level for target in targetList))
            else:
                bonusDamage = int(ceil(max(target.level for target in targetList) / 2.))
        else:
            bonusDamage = 0

        for target in targetList:
            if target not in targets:
                self.notify.debug("The target is not accessible!")
                continue

            attackDamage = receiveDamageCalc(self.battle, atkLevel, atkTrack, target, toon,
                                             PropAndPrestigeStack) + bonusDamage

            targetsHit += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, attackDamage))

            if target.getStatus(LURED_STATUS):
                self.notify.debug('Sound on lured suit, ' + 'indicating with KB_BONUS_COL flag')
                pos = self.battle.activeSuits.index(target)
                attack[TOON_KBBONUS_COL][pos] = KB_BONUS_LURED_FLAG
                messenger.send('delayed-wake', [toonId, target])
                messenger.send('lured-hit-exp', [attack, target])

            results[targets.index(target)] = attackDamage
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsHit > 0
