def genRewardDicts(entries):
    toonRewardDicts = []
    for toonId, origExp, earnedExp, origQuests, items, missedItems, origMerits, merits, parts in entries:
        if toonId != -1:
            toon = base.cr.doId2do.get(toonId)
            if toon is None:
                continue
            rewardDict = {'toon': toon,
                          'origExp': origExp, 'earnedExp': earnedExp,
                          'origQuests': origQuests, 'items': items, 'missedItems': missedItems,
                          'origMerits': origMerits, 'merits': merits,
                          'parts': parts}
            toonRewardDicts.append(rewardDict)

    return toonRewardDicts
