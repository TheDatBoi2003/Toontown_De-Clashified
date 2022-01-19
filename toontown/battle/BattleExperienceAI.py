from direct.directnotify import DirectNotifyGlobal
from toontown.toonbase import ToontownBattleGlobals
from toontown.suit import SuitDNA

BattleExperienceAINotify = DirectNotifyGlobal.directNotify.newCategory('BattleExprienceAI')


def getSkillGained(toonSkillPtsGained, toonId, track):
    exp = 0
    expList = toonSkillPtsGained.get(toonId, None)
    if expList:
        exp = expList[track]
    return int(exp + 0.5)


def getBattleExperience(activeToons, toonExp, toonSkillPtsGained, toonOrigQuests, toonItems, toonOrigMerits,
                        toonMerits, toonParts, suitsKilled, helpfulToonsList=None):
    rewardPool = []
    deathList = []
    toonIndices = {}

    for toonId in activeToons:
        rewardSet = []
        toon = simbase.air.doId2do.get(toonId)
        if toon:
            rewardSet.append(toonId)
            origExp = toonExp[toonId]
            earnedExp = []
            for i in xrange(len(ToontownBattleGlobals.Tracks)):
                earnedExp.append(getSkillGained(toonSkillPtsGained, toonId, i))

            rewardSet.append(origExp)
            rewardSet.append(earnedExp)
            origQuests = toonOrigQuests.get(toonId, [])
            rewardSet.append(origQuests)
            items = toonItems.get(toonId, ([], []))
            rewardSet.append(items[0])
            rewardSet.append(items[1])
            origMerits = toonOrigMerits.get(toonId, [])
            rewardSet.append(origMerits)
            merits = toonMerits.get(toonId, [0, 0, 0, 0])
            rewardSet.append(merits)
            parts = toonParts.get(toonId, [0, 0, 0, 0])
            rewardSet.append(parts)

            toonIndices[toonId] = activeToons.index(toonId)
            rewardPool.append(rewardSet)

    for deathRecord in suitsKilled:
        level = deathRecord['level']
        headType = deathRecord['type']
        if 'isVP' in deathRecord or 'isCFO' in deathRecord:
            level = 0
            typeNum = SuitDNA.suitDepts.index(deathRecord['track'])
        else:
            typeNum = SuitDNA.suitHeadTypes.index(headType)
        involvedToonIds = deathRecord['activeToons']
        toonBits = 0
        for toonId in involvedToonIds:
            if toonId in activeToons:
                toonBits |= 1 << toonIndices[toonId]

        flags = 0
        if 'isSkelecog' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_SKELECOG
        if 'isForeman' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_FOREMAN
        if 'isVP' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_VP
        if 'isCFO' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_CFO
        if 'isSupervisor' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_SUPERVISOR
        if 'isVirtual' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_VIRTUAL
        if 'hasRevives' in deathRecord:
            flags |= ToontownBattleGlobals.DLF_REVIVES
        deathList.extend([typeNum, level, toonBits, flags])

    return rewardPool, deathList, helpfulToonsList


def assignRewards(activeToons, toonSkillPtsGained, suitsKilled, zoneId, helpfulToons=None):
    if helpfulToons is None:
        BattleExperienceAINotify.warning('=============\nERROR ERROR helpfulToons=None in assignRewards , tell Red')
    activeToonList = []
    for t in activeToons:
        toon = simbase.air.doId2do.get(t)
        if toon:
            activeToonList.append(toon)

    for toon in activeToonList:
        for i in xrange(len(ToontownBattleGlobals.Tracks)):
            exp = getSkillGained(toonSkillPtsGained, toon.doId, i)
            totalExp = exp + toon.experience.getExp(i)
            if totalExp >= ToontownBattleGlobals.MaxSkill:
                toon.experience.setExp(i, ToontownBattleGlobals.MaxSkill)
            else:
                if exp > 0:
                    newGagList = toon.experience.getNewGagIndexList(i, exp)
                    toon.experience.addExp(i, amount=exp)
                    toon.inventory.addItemWithList(i, newGagList)
        toon.b_setExperience(toon.experience.makeNetString())
        toon.d_setInventory(toon.inventory.makeNetString())
        toon.b_setAnimState('victory', 1)

        if simbase.air.config.GetBool('battle-passing-no-credit', True):
            if helpfulToons and toon.doId in helpfulToons:
                simbase.air.questManager.toonKilledCogs(toon, suitsKilled, zoneId, activeToonList)
                simbase.air.cogPageManager.toonKilledCogs(toon, suitsKilled, zoneId)
            else:
                BattleExperienceAINotify.debug('toon=%d unhelpful not getting killed cog quest credit' % toon.doId)
        else:
            simbase.air.questManager.toonKilledCogs(toon, suitsKilled, zoneId, activeToonList)
            simbase.air.cogPageManager.toonKilledCogs(toon, suitsKilled, zoneId)

    return
