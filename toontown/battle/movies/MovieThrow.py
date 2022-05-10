from direct.interval.IntervalGlobal import *

import MovieCamera
import MovieUtil
from MovieUtil import calcAvgSuitPos
from toontown.battle.BattleBase import *
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleSounds import *
from toontown.suit.SuitDNA import *
from toontown.toon.ToonDNA import *

notify = DirectNotifyGlobal.directNotify.newCategory('MovieThrow')
hitSoundFiles = ('AA_tart_only.ogg', 'AA_slice_only.ogg',
                 'AA_slice_only.ogg', 'AA_slice_only.ogg',
                 'AA_wholepie_only.ogg', 'AA_throw_cream_pie_cog.ogg',
                 'AA_throw_wedding_cake_cog.ogg', 'AA_throw_wedding_cake_cog.ogg')
splatDict = {0: 'tiny_splat_cake', 1: 'tiny_splat_fruit', 2: 'tiny_splat_cream',
             3: 'splat_cake', 4: 'splat_fruit', 5: 'splat_cream', 6: 'splat_cake', 7: 'splat_cake'}
tPieLeavesHand = 2.7
tPieHitsSuit = 3.0
tSuitDodges = 2.45
ratioMissToHit = 1.5
tPieShrink = 0.7
pieFlyTaskName = 'MovieThrow-pieFly'


def addHit(suitDict, suitId, hitCount):
    if suitId in suitDict:
        suitDict[suitId] += hitCount
    else:
        suitDict[suitId] = hitCount


def doThrows(throws):
    if len(throws) == 0:
        return None, None
    suitThrowsDict = {}
    for throw in throws:
        if attackAffectsGroup(throw['track'], throw['level']):
            pass
        else:
            suitId = throw['target']['suit'].doId
            if suitId in suitThrowsDict:
                suitThrowsDict[suitId].append(throw)
            else:
                suitThrowsDict[suitId] = [throw]

    suitThrows = MovieUtil.sortAttacks(suitThrowsDict)
    totalHitDict = {}
    singleHitDict = {}
    groupHitDict = {}
    
    for throw in throws:
        if attackAffectsGroup(throw['track'], throw['level']):
            for i in xrange(len(throw['target'])):
                target = throw['target'][i]
                suitId = target['suit'].doId
                if target['hp'] > 0:
                    addHit(groupHitDict, suitId, 1)
                    addHit(totalHitDict, suitId, 1)
                else:
                    addHit(groupHitDict, suitId, 0)
                    addHit(totalHitDict, suitId, 0)

        else:
            suitId = throw['target']['suit'].doId
            if throw['target']['hp'] > 0:
                addHit(singleHitDict, suitId, 1)
                addHit(totalHitDict, suitId, 1)
            else:
                addHit(singleHitDict, suitId, 0)
                addHit(totalHitDict, suitId, 0)

    notify.debug('singleHitDict = %s' % singleHitDict)
    notify.debug('groupHitDict = %s' % groupHitDict)
    notify.debug('totalHitDict = %s' % totalHitDict)
    delay = 0.0
    mainTrack = Parallel()
    for suitThrow in suitThrows:
        if len(suitThrow) > 0:
            throwFunct = __doSuitThrows(suitThrow)
            if throwFunct:
                mainTrack.append(Sequence(Wait(delay), throwFunct))
            delay = delay + TOON_THROW_SUIT_DELAY

    retTrack = Sequence()
    retTrack.append(mainTrack)
    camDuration = retTrack.getDuration()
    camTrack = MovieCamera.chooseThrowShot(throws, suitThrowsDict, camDuration)
    return retTrack, camTrack


def __doSuitThrows(throws):
    toonTracks = Parallel()
    delay = 0.0
    hitCount = 0
    for throw in throws:
        if throw['target']['hp'] > 0:
            hitCount += 1
        else:
            break

    for throw in throws:
        tracks = __throwPie(throw, delay, hitCount)
        if tracks:
            for track in tracks:
                toonTracks.append(track)

        delay = delay + TOON_THROW_DELAY

    return toonTracks


def __showProp(prop, parent, pos):
    prop.reparentTo(parent)
    prop.setPos(pos)


def __animProp(props, propName, propType):
    if 'actor' == propType:
        for prop in props:
            prop.play(propName)

    elif 'model' == propType:
        pass
    else:
        notify.error('No such propType as: %s' % propType)


def __billboardProp(prop):
    scale = prop.getScale()
    prop.setBillboardPointWorld()
    prop.setScale(scale)


def __suitMissPoint(suit, other=render):
    pnt = suit.getPos(other)
    pnt.setZ(pnt[2] + suit.getHeight() * 1.3)
    return pnt


def __propPreflight(props, suit, toon, battle):
    prop = props[0]
    toon.update(0)
    prop.wrtReparentTo(battle)
    props[1].reparentTo(hidden)
    for ci in xrange(prop.getNumChildren()):
        prop.getChild(ci).setHpr(0, -90, 0)

    targetPnt = MovieUtil.avatarFacePoint(suit, other=battle)
    prop.lookAt(targetPnt)


def __propPreflightGroup(props, suits, toon, battle):
    prop = props[0]
    toon.update(0)
    prop.wrtReparentTo(battle)
    props[1].reparentTo(hidden)
    for ci in xrange(prop.getNumChildren()):
        prop.getChild(ci).setHpr(0, -90, 0)

    avgTargetPt = Point3(0, 0, 0)
    for suit in suits:
        avgTargetPt += MovieUtil.avatarFacePoint(suit, other=battle)

    avgTargetPt /= len(suits)
    prop.lookAt(avgTargetPt)


def __piePreMiss(missDict, pie, suitPoint, other=render):
    missDict['pie'] = pie
    missDict['startScale'] = pie.getScale()
    missDict['startPos'] = pie.getPos(other)
    v = Vec3(suitPoint - missDict['startPos'])
    endPos = missDict['startPos'] + v * ratioMissToHit
    missDict['endPos'] = endPos


def __pieMissLerpCallback(t, missDict):
    pie = missDict['pie']
    newPos = missDict['startPos'] * (1.0 - t) + missDict['endPos'] * t
    if t < tPieShrink:
        tScale = 0.0001
    else:
        tScale = (t - tPieShrink) / (1.0 - tPieShrink)
    newScale = missDict['startScale'] * max(1.0 - tScale, 0.01)
    pie.setPos(newPos)
    pie.setScale(newScale)


def __piePreMissGroup(missDict, pies, suitPoint, other=render):
    missDict['pies'] = pies
    missDict['startScale'] = pies[0].getScale()
    missDict['startPos'] = pies[0].getPos(other)
    v = Vec3(suitPoint - missDict['startPos'])
    endPos = missDict['startPos'] + v * ratioMissToHit
    missDict['endPos'] = endPos
    notify.debug('startPos=%s' % missDict['startPos'])
    notify.debug('v=%s' % v)
    notify.debug('endPos=%s' % missDict['endPos'])


def __pieMissGroupLerpCallback(t, missDict):
    pies = missDict['pies']
    newPos = missDict['startPos'] * (1.0 - t) + missDict['endPos'] * t
    if t < tPieShrink:
        tScale = 0.0001
    else:
        tScale = (t - tPieShrink) / (1.0 - tPieShrink)
    newScale = missDict['startScale'] * max(1.0 - tScale, 0.01)
    for pie in pies:
        pie.setPos(newPos)
        pie.setScale(newScale)


def __getWeddingCakeSoundTrack(hitSuit, node=None):
    throwTrack = Sequence()
    if hitSuit:
        throwSound = globalBattleSoundCache.getSound('AA_throw_wedding_cake.ogg')
        songTrack = Sequence()
        songTrack.append(Wait(1.0))
        songTrack.append(SoundInterval(throwSound, node=node))
        splatSound = globalBattleSoundCache.getSound('AA_throw_wedding_cake_cog.ogg')
        splatTrack = Sequence()
        splatTrack.append(Wait(tPieHitsSuit))
        splatTrack.append(SoundInterval(splatSound, node=node))
        throwTrack.append(Parallel(songTrack, splatTrack))
    else:
        throwSound = globalBattleSoundCache.getSound('AA_throw_wedding_cake_miss.ogg')
        throwTrack.append(Wait(tSuitDodges))
        throwTrack.append(SoundInterval(throwSound, node=node))
    return throwTrack


def __getSoundTrack(level, hitSuit, node=None):
    if level == WEDDING_LEVEL_INDEX:
        return __getWeddingCakeSoundTrack(hitSuit, node)
    throwSound = globalBattleSoundCache.getSound('AA_pie_throw_only.ogg')
    throwTrack = Sequence(Wait(2.6), SoundInterval(throwSound, node=node))
    if hitSuit:
        hitSound = globalBattleSoundCache.getSound(hitSoundFiles[level])
        hitTrack = Sequence(Wait(tPieLeavesHand), SoundInterval(hitSound, node=node))
        return Parallel(throwTrack, hitTrack)
    else:
        return throwTrack


def __throwPie(throw, delay, hitCount):
    toon = throw['toon']
    target = throw['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    sidestep = throw['sidestep']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    level = throw['level']
    battle = throw['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    notify.debug('toon: %s throws tart at suit: %d for hp: %d died: %d' % (toon.getName(), suit.doId, hp, died))
    pieName = pieNames[level]
    hitSuit = hp > 0
    pie = globalPropPool.getProp(pieName)
    pieType = globalPropPool.getPropType(pieName)
    pie2 = MovieUtil.copyProp(pie)
    pies = [pie, pie2]
    hands = toon.getRightHands()
    splatName = 'splat-' + pieName
    if pieName == 'wedding-cake':
        splatName = 'splat-birthday-cake'
    splat = globalPropPool.getProp(splatName)
    toonTrack = toonThrowTrack(toon, battle, delay, suitPos, origHpr)
    pieShow = Func(MovieUtil.showProps, pies, hands)
    pieAnim = Func(__animProp, pies, pieName, pieType)
    pieScale1 = LerpScaleInterval(pie, 1.0, pie.getScale(), startScale=MovieUtil.PNT3_NEARZERO)
    pieScale2 = LerpScaleInterval(pie2, 1.0, pie2.getScale(), startScale=MovieUtil.PNT3_NEARZERO)
    pieScale = Parallel(pieScale1, pieScale2)
    piePreflight = Func(__propPreflight, pies, suit, toon, battle)
    pieTrack = Sequence(Wait(delay), pieShow, pieAnim, pieScale, Func(battle.movie.needRestoreRenderProp, pies[0]),
                        Wait(tPieLeavesHand - 1.0), piePreflight)
    soundTrack = __getSoundTrack(level, hitSuit, toon)
    if hitSuit:
        pieFly = LerpPosInterval(pie, tPieHitsSuit - tPieLeavesHand, pos=MovieUtil.avatarFacePoint(suit, other=battle),
                                 name=pieFlyTaskName, other=battle)
        pieHide = Func(MovieUtil.removeProps, pies)
        splatShow = Func(__showProp, splat, suit, Point3(0, 0, suit.getHeight()))
        splatBillboard = Func(__billboardProp, splat)
        splatAnim = ActorInterval(splat, splatName)
        splatHide = Func(MovieUtil.removeProp, splat)
        pieTrack.append(pieFly)
        pieTrack.append(pieHide)
        pieTrack.append(Func(battle.movie.clearRenderProp, pies[0]))
        pieTrack.append(splatShow)
        pieTrack.append(splatBillboard)
        pieTrack.append(splatAnim)
        pieTrack.append(splatHide)
    else:
        missDict = {}
        if sidestep:
            suitPoint = MovieUtil.avatarFacePoint(suit, other=battle)
        else:
            suitPoint = __suitMissPoint(suit, other=battle)
        piePreMiss = Func(__piePreMiss, missDict, pie, suitPoint, battle)
        pieMiss = LerpFunctionInterval(__pieMissLerpCallback, extraArgs=[missDict],
                                       duration=(tPieHitsSuit - tPieLeavesHand) * ratioMissToHit)
        pieHide = Func(MovieUtil.removeProps, pies)
        pieTrack.append(piePreMiss)
        pieTrack.append(pieMiss)
        pieTrack.append(pieHide)
        pieTrack.append(Func(battle.movie.clearRenderProp, pies[0]))
    if hitSuit:
        suitResponseTrack = Sequence()
        showDamage = Func(suit.showHpText, -hp, openEnded=0, attackTrack=THROW_TRACK)
        if kbBonus > 0:
            anim = 'pie-small-react'
            suitInterval = MovieUtil.startSuitKnockbackInterval(suit, anim, battle)
        elif hitCount == 1:
            suitInterval = Parallel(ActorInterval(suit, 'pie-small-react'),
                                    MovieUtil.createSuitStunInterval(suit, 0.3, 1.3))
        else:
            suitInterval = ActorInterval(suit, 'pie-small-react')
        suitResponseTrack.append(Wait(delay + tPieHitsSuit))
        suitResponseTrack.append(showDamage)
        if toon.getTrackPrestige(THROW_TRACK):
            suitResponseTrack.append(Func(__splatSuit, suit, level))
        suitResponseTrack.append(Func(suit.updateHealthBar, hp))
        suitResponseTrack.append(suitInterval)
        bonusTrack = Sequence(Wait(delay + tPieHitsSuit))
        if kbBonus > 0:
            bonusTrack.append(Wait(0.75))
            bonusTrack.append(Func(suit.showHpText, -kbBonus, 2, openEnded=0, attackTrack=THROW_TRACK))
            bonusTrack.append(Func(suit.updateHealthBar, kbBonus))
        if hpBonus > 0:
            bonusTrack.append(Wait(0.75))
            bonusTrack.append(Func(suit.showHpText, -hpBonus, 1, openEnded=0, attackTrack=THROW_TRACK))
            bonusTrack.append(Func(suit.updateHealthBar, hpBonus))
        if revived != 0:
            suitResponseTrack.append(MovieUtil.createSuitReviveTrack(suit, battle))
        elif died != 0:
            suitResponseTrack.append(MovieUtil.createSuitDeathTrack(suit, battle))
        else:
            suitResponseTrack.append(Func(suit.doNeutralAnim))
        suitResponseTrack = Parallel(suitResponseTrack, bonusTrack)
    else:
        suitResponseTrack = MovieUtil.createSuitDodgeMultitrack(delay + tSuitDodges, suit, leftSuits, rightSuits)
    if not hitSuit and delay > 0:
        return [toonTrack, soundTrack, pieTrack]
    else:
        return [toonTrack,
                soundTrack,
                pieTrack,
                suitResponseTrack]


def __splatSuit(suit, level):
    splatTex = loader.loadTexture('phase_5/maps/' + splatDict[level] + '.png')
    splat = TextureStage(splatDict[level])
    splat.setMode(TextureStage.MDecal)
    if suit.isSkeleton:
        suit.setTexture(splat, splatTex)
    else:
        for headPart in suit.headParts:
            headPart.setTexture(splat, splatTex)
        suit.find('**/torso').setTexture(splat, splatTex)
        suit.find('**/arms').setTexture(splat, splatTex)
        suit.find('**/legs').setTexture(splat, splatTex)
        suit.find('**/hands').setTexture(splat, splatTex)


def toonThrowTrack(toon, battle, delay, suitPos, origHpr):
    return Sequence(Wait(delay), Func(toon.headsUp, battle, suitPos), ActorInterval(toon, 'throw'),
                    Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))


def changeCakePartParent(pie, cakeParts):
    pieParent = pie.getParent()
    notify.debug('pieParent = %s' % pieParent)
    for cakePart in cakeParts:
        cakePart.wrtReparentTo(pieParent)
