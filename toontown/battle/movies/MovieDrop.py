from direct.interval.IntervalGlobal import *

import toontown.battle.movies.MovieUtil
from toontown.battle.BattleBase import *
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleSounds import *
import MovieCamera
from direct.directnotify import DirectNotifyGlobal
import MovieUtil
import MovieNPCSOS
from MovieUtil import calcAvgSuitPos
from direct.showutil import Effects

from toontown.battle.movies import BattleParticles, MovieFire

notify = DirectNotifyGlobal.directNotify.newCategory('MovieDrop')
hitSoundFiles = (
    'AA_drop_flowerpot.ogg', 'AA_drop_sandbag.ogg', 'AA_drop_bowlingball.ogg', 'AA_drop_anvil.ogg',
    'AA_drop_bigweight.ogg',
    'AA_drop_safe.ogg', 'AA_drop_boulder.ogg', 'AA_drop_piano.ogg', 'AA_drop_boat.ogg')
missSoundFiles = (
    'AA_drop_flowerpot_miss.ogg', 'AA_drop_sandbag_miss.ogg', 'AA_drop_anvil_miss.ogg', 'AA_drop_anvil_miss.ogg',
    'AA_drop_bigweight_miss.ogg', 'AA_drop_safe_miss.ogg', 'AA_drop_boulder_miss.ogg', 'AA_drop_piano_miss.ogg',
    'AA_drop_boat_miss.ogg')
crashSounds = ('cogbldg_land.ogg', 'TL_train_cog.ogg')
tDropShadow = 1.3
tSuitDodges = 2.45 + tDropShadow
tObjectAppears = 3.0 + tDropShadow
tButtonPressed = 2.44
dShrink = 0.3
dShrinkOnMiss = 0.1
dPropFall = 0.6
objects = ('flowerpot', 'sandbag', 'bowlingball', 'anvil', 'weight', 'safe', 'boulder', 'piano', 'ship')
objZOffsets = (0.75, 0.75, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
objStartingScale = 1.0
landFrames = (12, 4, 4, 1, 11, 11, 11, 11, 2)
shoulderHeights = {'a': 13.28 / 4.0,
                   'b': 13.74 / 4.0,
                   'c': 10.02 / 4.0}


def __isMajorObject(level):
    return level > ANVIL_LEVEL_INDEX


def doDrops(drops):
    if len(drops) == 0:
        return None, None
    npcArrintervals, npcDepartures, npcToons = MovieNPCSOS.doNPCTeleports(drops)
    suitDropsDict = {}
    groupDrops = []
    for drop in drops:
        track = drop['track']
        level = drop['level']
        targets = drop['target']
        if len(targets) == 1:
            suitId = targets[0]['suit'].doId
            if suitId in suitDropsDict:
                suitDropsDict[suitId].append((drop, targets[0]))
            else:
                suitDropsDict[suitId] = [(drop, targets[0])]
        elif level == SHIP_LEVEL_INDEX:
            groupDrops.append(drop)
        else:
            for target in targets:
                suitId = target['suit'].doId
                if suitId in suitDropsDict:
                    otherDrops = suitDropsDict[suitId]
                    alreadyInList = 0
                    for oDrop in otherDrops:
                        if oDrop[0]['toon'] == drop['toon']:
                            alreadyInList = 1

                    if alreadyInList == 0:
                        suitDropsDict[suitId].append((drop, target))
                else:
                    suitDropsDict[suitId] = [(drop, target)]

    suitDrops = MovieUtil.sortAttacks(suitDropsDict)

    delay = 0.0
    mainTrack = Parallel(name='toplevel-drop')
    npcDrops = {}
    for st in suitDrops:
        if len(st) > 0:
            interval = __doSuitDrops(st, npcToons, npcDrops)
            if interval:
                mainTrack.append(Sequence(Wait(delay), interval))
            delay = delay + TOON_DROP_SUIT_DELAY

    dropTrack = Sequence(npcArrintervals, mainTrack, npcDepartures)
    camDuration = mainTrack.getDuration()
    if groupDrops:
        interval = __doGroupDrops(groupDrops)
        dropTrack.append(interval)
        camDuration += interval.getDuration()
    enterDuration = npcArrintervals.getDuration()
    exitDuration = npcDepartures.getDuration()
    camTrack = MovieCamera.chooseDropShot(drops, suitDropsDict, camDuration, enterDuration, exitDuration)
    return dropTrack, camTrack


def __getSoundTrack(level, delay, hitSuit, node=None, partial=0):
    if hitSuit:
        soundEffect = globalBattleSoundCache.getSound(hitSoundFiles[level])
    else:
        soundEffect = globalBattleSoundCache.getSound(missSoundFiles[level])
    soundTrack = Sequence()
    if soundEffect:
        buttonSound = globalBattleSoundCache.getSound('AA_drop_trigger_box.ogg')
        fallingSound = None
        buttonDelay = tButtonPressed - 0.3
        fallingDuration = 1.5
        if not level == SHIP_LEVEL_INDEX:
            fallingSound = globalBattleSoundCache.getSound('incoming_whistleALT.ogg')
        soundTrack.append(Wait(buttonDelay + delay))
        soundTrack.append(SoundInterval(buttonSound, duration=0.67, node=node))
        if fallingSound:
            soundTrack.append(SoundInterval(fallingSound, duration=fallingDuration, node=node))
        if not level == SHIP_LEVEL_INDEX:
            if hitSuit and partial and level > ANVIL_LEVEL_INDEX:
                soundTrack.append(SoundInterval(soundEffect, duration=2.6, node=node))
            else:
                soundTrack.append(SoundInterval(soundEffect, node=node))
        if level == SHIP_LEVEL_INDEX:
            if hitSuit:
                uberDelay = tButtonPressed
            else:
                uberDelay = tButtonPressed - 0.1
            oldSoundTrack = soundTrack
            soundTrack = Parallel()
            soundTrack.append(oldSoundTrack)
            uberTrack = Sequence()
            uberTrack.append(Wait(uberDelay))
            uberTrack.append(SoundInterval(soundEffect, node=node))
            soundTrack.append(uberTrack)
    else:
        soundTrack.append(Wait(0.1))
    return soundTrack


def __doSuitDrops(dropTargetPairs, npcs, npcDrops):
    toonTracks = Parallel()
    delay = 0.0
    alreadyDodged = 0
    alreadyTeased = 0
    for dropTargetPair in dropTargetPairs:
        drop = dropTargetPair[0]
        level = drop['level']
        objName = objects[level]
        target = dropTargetPair[1]
        lastDrop = dropTargetPairs.index(dropTargetPair) == len(dropTargetPairs) - 1
        track = __dropObjectForSingle(drop, delay, objName, level, alreadyDodged, alreadyTeased, npcs, target, npcDrops, lastDrop)
        if track:
            toonTracks.append(track)
            delay += TOON_DROP_DELAY
        hp = target['hp']
        if hp <= 0:
            if level > ANVIL_LEVEL_INDEX:
                alreadyTeased = 1
            else:
                alreadyDodged = 1

    return toonTracks


def __doGroupDrops(groupDrops):
    toonTracks = Parallel()
    delay = 0.0
    alreadyDodged = 0
    alreadyTeased = 0
    for drop in groupDrops:
        battle = drop['battle']
        level = drop['level']
        centerPos = calcAvgSuitPos(drop)
        targets = drop['target']
        numTargets = len(targets)
        closestTarget = -1
        nearestDistance = 100000.0
        for i in xrange(numTargets):
            suit = drop['target'][i]['suit']
            suitPos = suit.getPos(battle)
            displacement = Vec3(centerPos)
            displacement -= suitPos
            distance = displacement.lengthSquared()
            if distance < nearestDistance:
                closestTarget = i
                nearestDistance = distance

        lastDrop = groupDrops.index(drop) == len(groupDrops) - 1
        track = __dropGroupObject(drop, delay, closestTarget, alreadyDodged, alreadyTeased, lastDrop)
        if track:
            toonTracks.append(track)
            delay = delay + TOON_DROP_SUIT_DELAY
        hp = drop['target'][closestTarget]['hp']
        if hp <= 0:
            if level > ANVIL_LEVEL_INDEX:
                alreadyTeased = 1
            else:
                alreadyDodged = 1

    return toonTracks


def __dropGroupObject(drop, delay, closestTarget, alreadyDodged, alreadyTeased, lastDrop=0):
    level = drop['level']
    objName = objects[level]
    target = drop['target'][closestTarget]
    npcDrops = {}
    npcs = []
    returnedParallel = __dropObject(drop, delay, objName, level, target, npcDrops, lastDrop)
    for i in xrange(len(drop['target'])):
        target = drop['target'][i]
        suitTrack = __createSuitTrack(drop, delay, level, alreadyDodged, alreadyTeased, target, npcs, lastDrop)
        if suitTrack:
            returnedParallel.append(suitTrack)

    return returnedParallel


def __dropObjectForSingle(drop, delay, objName, level, alreadyDodged, alreadyTeased, npcs, target, npcDrops, lastDrop=0):
    singleDropParallel = __dropObject(drop, delay, objName, level, target, npcDrops, lastDrop)
    suitTrack = __createSuitTrack(drop, delay, level, alreadyDodged, alreadyTeased, target, npcs, lastDrop)
    if suitTrack:
        singleDropParallel.append(suitTrack)
    return singleDropParallel


def __dropObject(drop, delay, objName, level, target, npcDrops, lastDrop):
    toon = drop['toon']
    repeatNPC = 0
    battle = drop['battle']
    if 'npc' in drop:
        toon = drop['npc']
        if toon in npcDrops:
            repeatNPC = 1
        else:
            npcDrops[toon] = 1
        origHpr = Vec3(0, 0, 0)
    else:
        origHpr = toon.getHpr(battle)
    suit = target['suit']
    hp = target['hp']
    died = target['died']
    hitSuit = hp > 0
    suitPos = suit.getPos(battle)
    majorObject = __isMajorObject(level)
    propObject = globalPropPool.getProp(objName)
    if objName == 'weight':
        propObject.setScale(propObject.getScale() * 0.75)
    elif objName == 'safe':
        propObject.setScale(propObject.getScale() * 0.85)
    elif objName == 'boulder':
        propObject.setScale(propObject.getScale() * 1.2)
    node = propObject.node()
    node.setBounds(OmniBoundingVolume())
    node.setFinal(1)
    soundTrack = __getSoundTrack(level, delay, hitSuit, toon, died or not lastDrop)
    if not repeatNPC:
        toonTrack, buttonTrack = MovieUtil.createButtonInterval(battle, delay, origHpr, suitPos, toon)
    objectTrack = Sequence()

    def posProp(prop, miss):
        prop.reparentTo(battle)
        if battle.isSuitLured(suit):
            pos, hpr = battle.getActorPosHpr(suit)
            prop.setPos(pos)
            prop.setHpr(hpr)
            if majorObject:
                prop.setY(prop.getY() + 2)
        else:
            prop.setPos(suit.getPos(battle))
            prop.setHpr(suit.getHpr(battle))
            if miss and majorObject:
                prop.setY(prop.getY(battle) + 5)
        if not majorObject:
            if not miss:
                shoulderHeight = shoulderHeights[suit.style.body] * suit.scale
                prop.setZ(prop.getPos(battle)[2] + shoulderHeight)
        prop.setZ(prop.getPos(battle)[2] + objZOffsets[level])

    objectTrack.append(Func(battle.movie.needRestoreRenderProp, propObject))
    objInit = Func(posProp, propObject, hp <= 0)
    objectTrack.append(Wait(delay + tObjectAppears))
    objectTrack.append(objInit)
    if (hp > 0 and (not died and lastDrop)) or 0 < level <= ANVIL_LEVEL_INDEX:
        if hasattr(propObject, 'getAnimControls'):
            animProp = ActorInterval(propObject, objName)
            shrinkProp = LerpScaleInterval(propObject, dShrink, Point3(0.01, 0.01, 0.01),
                                           startScale=propObject.getScale())
            objAnimShrink = ParallelEndTogether(animProp, shrinkProp)
            objectTrack.append(objAnimShrink)
        else:
            startingScale = objStartingScale
            object2 = MovieUtil.copyProp(propObject)
            posProp(object2, hp <= 0)
            endingPos = object2.getPos()
            startPos = Point3(endingPos[0], endingPos[1], endingPos[2] + 5)
            startHpr = object2.getHpr()
            endHpr = Point3(startHpr[0] + 90, startHpr[1], startHpr[2])
            animProp = LerpPosInterval(propObject, landFrames[level] / 24.0, endingPos, startPos=startPos)
            shrinkProp = LerpScaleInterval(propObject, dShrink, Point3(0.01, 0.01, 0.01), startScale=startingScale)
            bounceProp = Effects.createZBounce(propObject, 2, endingPos, 0.5, 1.5)
            objAnimShrink = Sequence(Func(propObject.setScale, startingScale), Func(propObject.setH, endHpr[0]),
                                     animProp,
                                     bounceProp, Wait(1.5), shrinkProp)
            objectTrack.append(objAnimShrink)
            MovieUtil.removeProp(object2)
    elif hasattr(propObject, 'getAnimControls'):
        animProp = ActorInterval(propObject, objName, duration=landFrames[level] / 24.0)

        def poseProp(prop, animName):
            prop.pose(animName, landFrames[level])

        poseProp = Func(poseProp, propObject, objName)
        shrinkProp = LerpScaleInterval(propObject, dShrinkOnMiss, Point3(0.01, 0.01, 0.01),
                                       startScale=propObject.getScale())
        objectTrack.append(animProp)
        objectTrack.append(poseProp)
        objectTrack.append(Wait(0.8))
        objectTrack.append(shrinkProp)
    else:
        startingScale = objStartingScale
        object2 = MovieUtil.copyProp(propObject)
        posProp(object2, hp <= 0)
        endingPos = object2.getPos()
        startPos = Point3(endingPos[0], endingPos[1], endingPos[2] + 5)
        startHpr = object2.getHpr()
        endHpr = Point3(startHpr[0] + 90, startHpr[1], startHpr[2])
        animProp = LerpPosInterval(propObject, landFrames[level] / 24.0, endingPos, startPos=startPos)
        shrinkProp = LerpScaleInterval(propObject, dShrinkOnMiss, Point3(0.01, 0.01, 0.01), startScale=startingScale)
        bounceProp = Effects.createZBounce(propObject, 2, endingPos, 0.5, 1.5)
        objAnimShrink = Sequence(Func(propObject.setScale, startingScale), Func(propObject.setH, endHpr[0]), animProp,
                                 bounceProp, Wait(1.5), shrinkProp)
        objectTrack.append(objAnimShrink)
        MovieUtil.removeProp(object2)
    objectTrack.append(Func(MovieUtil.removeProp, propObject))
    objectTrack.append(Func(battle.movie.clearRenderProp, propObject))
    dropShadow = MovieUtil.copyProp(suit.getShadowJoint())
    if level == 0:
        dropShadow.setScale(0.5)
    elif level <= ANVIL_LEVEL_INDEX:
        dropShadow.setScale(0.8)
    elif level == ANVIL_LEVEL_INDEX + 1:
        dropShadow.setScale(2.0)
    elif level == ANVIL_LEVEL_INDEX + 2:
        dropShadow.setScale(2.3)
    elif level == SHIP_LEVEL_INDEX:
        dropShadow.setScale(3.6)
    else:
        dropShadow.setScale(2.6)

    def posShadow():
        dropShadow.reparentTo(battle)
        if battle.isSuitLured(suit):
            pos, hpr = battle.getActorPosHpr(suit)
            dropShadow.setPos(pos)
            dropShadow.setHpr(hpr)
            if __isMajorObject(level):
                dropShadow.setY(dropShadow.getY() + 2)
        else:
            dropShadow.setPos(suit.getPos(battle))
            dropShadow.setHpr(suit.getHpr(battle))
            if hp <= 0 and __isMajorObject(level):
                dropShadow.setY(dropShadow.getY(battle) + 5)
        dropShadow.setZ(dropShadow.getZ() + 0.5)

    shadowTrack = Sequence(Wait(delay + tButtonPressed), Func(battle.movie.needRestoreRenderProp, dropShadow),
                           Func(posShadow),
                           LerpScaleInterval(dropShadow, tObjectAppears - tButtonPressed, dropShadow.getScale(),
                                             startScale=Point3(0.01, 0.01, 0.01)), Wait(0.3),
                           Func(MovieUtil.removeProp, dropShadow), Func(battle.movie.clearRenderProp, dropShadow))
    return Parallel(toonTrack, soundTrack, buttonTrack, objectTrack, shadowTrack)


def __createSuitTrack(drop, delay, level, alreadyDodged, alreadyTeased, target, npcToons, lastDrop=0):
    toon = drop['toon']
    if 'npc' in drop:
        toon = drop['npc']
    battle = drop['battle']
    majorObject = __isMajorObject(level)
    suit = target['suit']
    hp = target['hp']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    headless = False
    if hp > 0:
        suitTrack = Sequence()
        showDamage = Func(suit.showHpText, -hp, openEnded=0)
        updateHealthBar = Func(suit.updateHealthBar, hp)
        if majorObject:
            anim = 'flatten'
        else:
            anim = 'drop-react'
        if died and lastDrop and __isMajorObject(level):
            suitReact = ActorInterval(suit, anim, endTime=0.55)
        elif not lastDrop:
            suitReact = ActorInterval(suit, anim, endTime=TOON_DROP_DELAY)
        else:
            suitReact = ActorInterval(suit, anim)
        suitTrack.append(Wait(delay + tObjectAppears))
        suitTrack.append(showDamage)
        suitTrack.append(updateHealthBar)
        suitGettingHit = Parallel(suitReact)
        if level == SHIP_LEVEL_INDEX:
            gotHitSound = globalBattleSoundCache.getSound('AA_drop_boat_cog.ogg')
            suitGettingHit.append(SoundInterval(gotHitSound, node=toon))
        if died and lastDrop:
            if level > ANVIL_LEVEL_INDEX:
                suitGettingHit.append(suitCrashTrack(suit))
                suitTrack.append(suitGettingHit)
                return suitTrack
            elif not suit.getSkelecog():
                headless = True
                suitGettingHit.append(MovieUtil.spawnHeadExplodeTrack(suit, battle))
        suitTrack.append(suitGettingHit)
        bonusTrack = None
        if 'hpBonus' in target:
            bonusTrack = Sequence(Wait(delay + tObjectAppears + 0.75),
                                  Func(suit.showHpText, -target['hpBonus'], 1, openEnded=0))
            bonusTrack.append(updateHealthBar)
        if revived != 0:
            suitTrack.append(MovieUtil.createSuitReviveTrack(suit, battle, npcToons))
        elif died != 0:
            suitTrack.append(MovieUtil.createSuitDeathTrack(suit, battle, npcToons, headless))
        else:
            suitTrack.append(Func(suit.loop, 'neutral'))
        if not bonusTrack:
            suitTrack = Parallel(suitTrack, bonusTrack)
    elif 'kbBonus' in target and target['kbBonus'] == 0:
        suitTrack = Sequence(Wait(delay + tObjectAppears), Func(MovieUtil.indicateMissed, suit, 0.6),
                             Func(suit.loop, 'neutral'))
    else:
        if alreadyDodged > 0:
            return
        if majorObject:
            if alreadyTeased > 0:
                return
            else:
                suitTrack = MovieUtil.createSuitTeaseMultiTrack(suit, delay=delay + tObjectAppears)
        else:
            suitTrack = MovieUtil.createSuitDodgeMultitrack(delay + tSuitDodges, suit, leftSuits, rightSuits)
    return suitTrack


def suitCrashTrack(suit):
    suitScale = suit.getScale()
    suitPos = suit.getPos()
    hitTime = 0.1
    shrinkStartDelay = 2.0
    crashSoundEffects = []
    for sound in crashSounds:
        crashSoundEffects.append(globalBattleSoundCache.getSound(sound))
    suitTrack = Sequence(Wait(hitTime),
                         Func(suit.setScale, Point3(suitScale[0], suitScale[1], suitScale[2] * 0.0001)),
                         Func(suit.setPos, Point3(suitPos[0], suitPos[1], suitPos[2] + 0.02)),
                         Func(suit.setColorScale, Vec4(0.0, 0.0, 0.0, 1)),
                         Func(suit.deleteNametag3d),
                         Func(suit.deleteDropShadow),
                         Wait(shrinkStartDelay),
                         LerpScaleInterval(suit, 0.8, Point3(0.0001, 0.0001, 0.0001), blendType='easeIn'),
                         Func(suit.hide))
    soundTrack = Parallel(SoundInterval(crashSoundEffects[0], node=suit),
                          SoundInterval(crashSoundEffects[1], node=suit))
    return Parallel(suitTrack, soundTrack)
