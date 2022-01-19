from direct.interval.IntervalGlobal import *

import BattleParticles
import MovieCamera
import MovieUtil
from BattleProps import *
from BattleSounds import *
from toontown.battle import MovieThrow
from toontown.battle.BattleBase import TOON_SQUIRT_SUIT_DELAY, TOON_SQUIRT_DELAY
from toontown.battle.MovieThrow import ratioMissToHit
from toontown.suit.SuitDNA import *
from toontown.toon.ToonDNA import *
from toontown.toonbase import ToontownBattleGlobals
from toontown.toonbase.ToontownBattleGlobals import *

notify = DirectNotifyGlobal.directNotify.newCategory('MovieSquirt')
hitSoundFiles = ('AA_squirt_flowersquirt.ogg', 'AA_squirt_glasswater.ogg', 'AA_squirt_neonwatergun.ogg',
                 'SA_watercooler_spray_only.ogg', 'AA_squirt_seltzer.ogg', 'firehose_spray.ogg',
                 'AA_throw_stormcloud.ogg', 'AA_squirt_Geyser.ogg')
missSoundFiles = ('AA_squirt_flowersquirt_miss.ogg', 'AA_squirt_glasswater_miss.ogg', 'AA_squirt_neonwatergun_miss.ogg',
                  'AA_pie_throw_only.ogg', 'AA_squirt_seltzer_miss.ogg', 'firehose_spray.ogg',
                  'AA_throw_stormcloud_miss.ogg', 'AA_squirt_Geyser.ogg')
sprayScales = [0.2, 0.3, 0.3, 0.4, 0.6, 0.8, 1.0, 2.0]
WaterSprayColor = Point4(0.75, 0.75, 1.0, 0.8)
SoakColor = Point4(0.65, 0.65, 1.0, 1.0)


def doSquirts(squirts):
    if len(squirts) == 0:
        return None, None

    suitSquirtsDict = {}
    for squirt in squirts:
        if type(squirt['target']) is []:
            target = squirt['target'][0]
            suitId = target['suit'].doId
            if suitId in suitSquirtsDict:
                suitSquirtsDict[suitId].append(squirt)
            else:
                suitSquirtsDict[suitId] = [squirt]
        else:
            suitId = squirt['target']['suit'].doId
            if suitId in suitSquirtsDict:
                suitSquirtsDict[suitId].append(squirt)
            else:
                suitSquirtsDict[suitId] = [squirt]

    suitSquirts = suitSquirtsDict.values()

    def compFunc(a, b):
        if len(a) > len(b):
            return 1
        elif len(a) < len(b):
            return -1
        return 0

    suitSquirts.sort(compFunc)

    delay = 0.0

    mainTrack = Parallel()
    for suitSquirt in suitSquirts:
        if len(suitSquirt) > 0:
            squirtFunct = __doSuitSquirts(suitSquirt)
            if squirtFunct:
                mainTrack.append(Sequence(Wait(delay), squirtFunct))
            delay = delay + TOON_SQUIRT_SUIT_DELAY

    camDuration = mainTrack.getDuration()
    camTrack = MovieCamera.chooseSquirtShot(squirts, suitSquirtsDict, camDuration)
    return mainTrack, camTrack


def clearSuitSoaks(soakRemovals):
    mainTrack = Parallel()
    for soakRemoval in soakRemovals:
        if len(soakRemoval) > 0:
            suit = soakRemoval['suit']
            mainTrack.append(Sequence(ActorInterval(suit, 'soak')))

    camDuration = mainTrack.getDuration()
    camTrack = MovieCamera.allGroupHighShot(None, camDuration)
    return mainTrack, camTrack


def __doSuitSquirts(squirts):
    toonTracks = Parallel()
    delay = 0.0
    fShowStun = 0
    if type(squirts[0]['target']) is []:
        for target in squirts[0]['target']:
            fShowStun = len(squirts) == 1 and target['hp'] > 0
    else:
        fShowStun = len(squirts) == 1 and squirts[0]['target']['hp'] > 0
    for s in squirts:
        tracks = __doSquirt(s, delay, fShowStun)
        if tracks:
            for track in tracks:
                toonTracks.append(track)

        delay = delay + TOON_SQUIRT_DELAY

    return toonTracks


def __doSquirt(squirt, delay, fShowStun):
    squirtSequence = Sequence(Wait(delay))
    if type(squirt['target']) is []:
        for target in squirt['target']:
            notify.debug('toon: %s squirts prop: %d at suit: %d for hp: %d' % (squirt['toon'].getName(),
                                                                               squirt['level'],
                                                                               target['suit'].doId,
                                                                               target['hp']))

    else:
        notify.debug('toon: %s squirts prop: %d at suit: %d for hp: %d' % (squirt['toon'].getName(),
                                                                           squirt['level'],
                                                                           squirt['target']['suit'].doId,
                                                                           squirt['target']['hp']))
    interval = squirtFunctions[squirt['level']](squirt, delay, fShowStun)
    if interval:
        squirtSequence.append(interval)
    return [squirtSequence]


def __suitTargetPoint(suit):
    pnt = suit.getPos(render)
    pnt.setZ(pnt[2] + suit.getHeight() * 0.66)
    return Point3(pnt)


def __getSplashTrack(point, splashScale, delay, battle, splashHold=0.01):
    def prepSplash(splashPoint):
        if callable(point):
            splashPoint = point()
        splash.reparentTo(render)
        splash.setPos(splashPoint)
        splash.setBillboardPointWorld()
        splash.setScale(splash.getScale())

    splash = globalPropPool.getProp('splash-from-splat')
    splash.setScale(splashScale)
    return Sequence(Func(battle.movie.needRestoreRenderProp, splash), Wait(delay), Func(prepSplash, point),
                    ActorInterval(splash, 'splash-from-splat'), Wait(splashHold), Func(MovieUtil.removeProp, splash),
                    Func(battle.movie.clearRenderProp, splash))


def __getSuitTrack(suit, tContact, tDodge, hp, hpBonus, kbBonus, anim, died, leftSuits, rightSuits,
                   battle, fShowStun, beforeStun=0.5, afterStun=1.8, attackLevel=-1, uberRepeat=0, revived=0, prest=0):
    if hp > 0:
        suitTrack = Sequence()
        geyser = attackLevel == ToontownBattleGlobals.MAX_LEVEL_INDEX
        if kbBonus > 0 and not geyser:
            suitPos, suitHpr = battle.getActorPosHpr(suit)
            suitType = getSuitBodyType(suit.getStyleName())
            animTrack = Sequence()
            animTrack.append(ActorInterval(suit, anim, duration=0.2))
            if suitType == 'a':
                animTrack.append(ActorInterval(suit, 'slip-forward', startTime=2.43))
            elif suitType == 'b':
                animTrack.append(ActorInterval(suit, 'slip-forward', startTime=1.94))
            elif suitType == 'c':
                animTrack.append(ActorInterval(suit, 'slip-forward', startTime=2.58))
            animTrack.append(Func(battle.unlureSuit, suit))
            moveTrack = Sequence(Wait(0.2), LerpPosInterval(suit, 0.6, pos=suitPos, other=battle))
            suitInterval = Parallel(animTrack, moveTrack)
        elif geyser:
            suitType = getSuitBodyType(suit.getStyleName())
            if suitType == 'a':
                startFlailFrame = 16
                endFlailFrame = 16
            elif suitType == 'b':
                startFlailFrame = 15
                endFlailFrame = 15
            else:
                startFlailFrame = 15
                endFlailFrame = 15
            suitInterval = Sequence(
                ActorInterval(suit, 'slip-backward', playRate=0.5, startFrame=0, endFrame=startFlailFrame - 1),
                Func(suit.pingpong, 'slip-backward', fromFrame=startFlailFrame, toFrame=endFlailFrame), Wait(0.5),
                ActorInterval(suit, 'slip-backward', playRate=1.0, startFrame=endFlailFrame))
        elif fShowStun == 1:
            suitBody = [suit.find('**/torso'), suit.find('**/arms'), suit.find('**/legs')]
            suitInterval = Parallel(ActorInterval(suit, anim),
                                    Sequence(Wait(beforeStun), Func(suitBody[0].setColor, SoakColor),
                                             Func(suitBody[1].setColor, SoakColor),
                                             Func(suitBody[2].setColor, SoakColor)),
                                    MovieUtil.createSuitStunInterval(suit, beforeStun, afterStun))
        else:
            suitBody = [suit.find('**/torso'), suit.find('**/arms'), suit.find('**/legs')]
            suitInterval = Parallel(ActorInterval(suit, anim),
                                    Sequence(Wait(beforeStun), Func(suitBody[0].setColor, SoakColor),
                                             Func(suitBody[1].setColor, SoakColor),
                                             Func(suitBody[2].setColor, SoakColor)))
        if prest:
            if len(leftSuits) >= 1:
                suitBody = [leftSuits[0].find('**/torso'), leftSuits[0].find('**/arms'), leftSuits[0].find('**/legs')]
                suitInterval = Parallel(suitInterval,
                                        ActorInterval(leftSuits[0], 'squirt-small-react'),
                                        Sequence(Wait(beforeStun), Func(suitBody[0].setColor, SoakColor),
                                                 Func(suitBody[1].setColor, SoakColor),
                                                 Func(suitBody[2].setColor, SoakColor)))
            if len(rightSuits) >= 1:
                suitBody = [rightSuits[0].find('**/torso'), rightSuits[0].find('**/arms'), rightSuits[0].find('**/legs')]
                suitInterval = Parallel(suitInterval,
                                        ActorInterval(rightSuits[0], 'squirt-small-react'),
                                        Sequence(Wait(beforeStun), Func(suitBody[0].setColor, SoakColor),
                                                 Func(suitBody[1].setColor, SoakColor),
                                                 Func(suitBody[2].setColor, SoakColor)))
        showDamage = Func(suit.showHpText, -hp, openEnded=0, attackTrack=SQUIRT_TRACK, attackLevel=attackLevel)
        updateHealthBar = Func(suit.updateHealthBar, hp)
        suitTrack.append(Wait(tContact))
        suitTrack.append(showDamage)
        suitTrack.append(updateHealthBar)
        if not geyser:
            suitTrack.append(suitInterval)
        elif not uberRepeat:
            suitStartPos = suit.getPos()
            suitFloat = Point3(0, 0, 14)
            suitEndPos = Point3(suitStartPos[0] + suitFloat[0], suitStartPos[1] + suitFloat[1],
                                suitStartPos[2] + suitFloat[2])
            suitUp = LerpPosInterval(suit, 1.1, suitEndPos, startPos=suitStartPos, fluid=1)
            suitDown = LerpPosInterval(suit, 0.6, suitStartPos, startPos=suitEndPos, fluid=1)
            geyserMotion = Sequence(suitUp, Wait(0.0), suitDown)
            suitLaunch = Parallel(suitInterval, geyserMotion)
            suitTrack.append(suitLaunch)
        else:
            suitTrack.append(Wait(5.5))
        bonusTrack = Sequence(Wait(tContact))
        if kbBonus > 0:
            bonusTrack.append(Wait(0.75))
            bonusTrack.append(Func(suit.showHpText, -kbBonus, 2, openEnded=0, attackTrack=SQUIRT_TRACK))
            bonusTrack.append(updateHealthBar)
        if hpBonus > 0:
            bonusTrack.append(Wait(0.75))
            bonusTrack.append(Func(suit.showHpText, -hpBonus, 1, openEnded=0, attackTrack=SQUIRT_TRACK))
            bonusTrack.append(updateHealthBar)
        if died:
            suitTrack.append(MovieUtil.createSuitDeathTrack(suit, battle))
        else:
            suitTrack.append(Func(suit.loop, 'neutral'))
        if revived:
            suitTrack.append(MovieUtil.createSuitReviveTrack(suit, battle))
        return Parallel(suitTrack, bonusTrack)
    else:
        return MovieUtil.createSuitDodgeMultitrack(tDodge, suit, leftSuits, rightSuits)


def say(statement):
    print statement


def __getSoundTrack(level, hitSuit, delay, node=None):
    if hitSuit:
        soundEffect = globalBattleSoundCache.getSound(hitSoundFiles[level])
    else:
        soundEffect = globalBattleSoundCache.getSound(missSoundFiles[level])
    soundTrack = Sequence()
    if soundEffect:
        soundTrack.append(Wait(delay))
        soundTrack.append(SoundInterval(soundEffect, node=node))
    return soundTrack


def __doFlower(squirt, delay, fShowStun):
    toon = squirt['toon']
    level = squirt['level']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    battle = squirt['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    hitSuit = hp > 0
    scale = sprayScales[level]
    tTotalFlowerToonAnimationTime = 2.5
    tFlowerFirstAppears = 1.0
    dFlowerScaleTime = 0.5
    tSprayStarts = tTotalFlowerToonAnimationTime
    dSprayScale = 0.2
    dSprayHold = 0.1
    tContact = tSprayStarts + dSprayScale
    tSuitDodges = tTotalFlowerToonAnimationTime
    tracks = Parallel()
    button = globalPropPool.getProp('button')
    button2 = MovieUtil.copyProp(button)
    buttons = [button, button2]
    hands = toon.getLeftHands()
    toonTrack = Sequence(Func(MovieUtil.showProps, buttons, hands), Func(toon.headsUp, battle, suitPos),
                         ActorInterval(toon, 'pushbutton'), Func(MovieUtil.removeProps, buttons),
                         Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    tracks.append(__getSoundTrack(level, hitSuit, tTotalFlowerToonAnimationTime - 0.4, toon))
    flower = globalPropPool.getProp('squirting-flower')
    flower.setScale(1.5, 1.5, 1.5)

    targetPoint = __suitTargetPoint(suit)

    def getSprayStartPos():
        toon.update(0)
        return flower.getPos(render)

    sprayTrack = MovieUtil.getSprayTrack(battle, WaterSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                         dSprayHold, dSprayScale, horizScale=scale, vertScale=scale)
    lodNames = toon.getLODNames()
    toonLOD0 = toon.getLOD(lodNames[0])
    toonLOD1 = toon.getLOD(lodNames[1])
    flowerJoint0 = None
    flowerJoint1 = None
    if base.config.GetBool('want-new-anims', 1):
        if not toonLOD0.find('**/def_joint_attachFlower').isEmpty():
            flowerJoint0 = toonLOD0.find('**/def_joint_attachFlower')
    else:
        flowerJoint0 = toonLOD0.find('**/joint_attachFlower')
    if base.config.GetBool('want-new-anims', 1):
        if not toonLOD1.find('**/def_joint_attachFlower').isEmpty():
            flowerJoint1 = toonLOD1.find('**/def_joint_attachFlower')
    else:
        flowerJoint1 = toonLOD1.find('**/joint_attachFlower')
    flowerJointPath0 = flowerJoint0.attachNewNode('attachFlower-InstanceNode')
    flowerJointPath1 = flowerJointPath0.instanceTo(flowerJoint1)
    flowerTrack = Sequence(Wait(tFlowerFirstAppears), Func(flower.reparentTo, flowerJointPath0),
                           LerpScaleInterval(flower, dFlowerScaleTime, flower.getScale(),
                                             startScale=MovieUtil.PNT3_NEARZERO),
                           Wait(tTotalFlowerToonAnimationTime - dFlowerScaleTime - tFlowerFirstAppears))
    if hp <= 0:
        flowerTrack.append(Wait(0.5))
    flowerTrack.append(sprayTrack)
    flowerTrack.append(LerpScaleInterval(flower, dFlowerScaleTime, MovieUtil.PNT3_NEARZERO))
    flowerTrack.append(Func(flowerJointPath1.removeNode))
    flowerTrack.append(Func(flowerJointPath0.removeNode))
    flowerTrack.append(Func(MovieUtil.removeProp, flower))
    tracks.append(flowerTrack)
    if hp > 0:
        tracks.append(__getSplashTrack(targetPoint, scale, tSprayStarts + dSprayScale, battle))
    if hp > 0 or delay <= 0:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'squirt-small-react', died, leftSuits,
                           rightSuits, battle, fShowStun, attackLevel=0, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doWaterGlass(squirt, delay, fShowStun):
    toon = squirt['toon']
    level = squirt['level']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    battle = squirt['battle']
    hitSuit = hp > 0
    scale = sprayScales[level]
    tSpray = 82.0 / toon.getFrameRate('spit')
    dSprayScale = 0.1
    dSprayHold = 0.1
    tContact = tSpray + dSprayScale
    tSuitDodges = max(tSpray - 0.5, 0.0)
    tracks = Parallel()
    tracks.append(ActorInterval(toon, 'spit'))
    soundTrack = __getSoundTrack(level, hitSuit, 1.7, toon)
    tracks.append(soundTrack)
    glass = globalPropPool.getProp('glass')
    hands = toon.getRightHands()
    handJointPath0 = hands[0].attachNewNode('handJoint0-path')
    handJointPath1 = handJointPath0.instanceTo(hands[1])
    glassTrack = Sequence(Func(MovieUtil.showProp, glass, handJointPath0), ActorInterval(glass, 'glass'),
                          Func(handJointPath1.removeNode), Func(handJointPath0.removeNode),
                          Func(MovieUtil.removeProp, glass))
    tracks.append(glassTrack)
    targetPoint = __suitTargetPoint(suit)

    def getSprayStartPos():
        toon.update(0)
        lod0 = toon.getLOD(toon.getLODNames()[0])
        if base.config.GetBool('want-new-anims', 1):
            if not lod0.find('**/def_head').isEmpty():
                joint = lod0.find('**/def_head')
            else:
                joint = lod0.find('**/joint_head')
        else:
            joint = lod0.find('**/joint_head')
        n = hidden.attachNewNode('pointInFrontOfHead')
        n.reparentTo(toon)
        n.setPos(joint.getPos(toon) + Point3(0, 0.3, -0.2))
        p = n.getPos(render)
        n.removeNode()
        del n
        return p

    sprayTrack = MovieUtil.getSprayTrack(battle, WaterSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                         dSprayHold, dSprayScale, horizScale=scale, vertScale=scale)
    tracks.append(Sequence(Wait(tSpray), sprayTrack))
    if hp > 0:
        tracks.append(__getSplashTrack(targetPoint, scale, tSpray + dSprayScale, battle))
    if hp > 0 or delay <= 0:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'squirt-small-react', died, leftSuits,
                           rightSuits, battle, fShowStun, attackLevel=1, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doWaterGun(squirt, delay, fShowStun):
    toon = squirt['toon']
    level = squirt['level']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    battle = squirt['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    hitSuit = hp > 0
    scale = sprayScales[level]
    dPistolScale = 0.5
    dPistolHold = 1.8
    tSpray = 48.0 / toon.getFrameRate('water-gun')
    dSprayScale = 0.1
    dSprayHold = 0.3
    tContact = tSpray + dSprayScale
    tSuitDodges = 1.1
    tracks = Parallel()
    toonTrack = Sequence(Func(toon.headsUp, battle, suitPos), ActorInterval(toon, 'water-gun'),
                         Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    soundTrack = __getSoundTrack(level, hitSuit, 1.8, toon)
    tracks.append(soundTrack)
    pistol = globalPropPool.getProp('water-gun')
    hands = toon.getRightHands()
    handJointPath0 = hands[0].attachNewNode('handJoint0-path')
    handJoinPath1 = handJointPath0.instanceTo(hands[1])
    targetPoint = __suitTargetPoint(suit)

    def getSprayStartPos():
        toon.update(0)
        joint = pistol.find('**/joint_nozzle')
        p = joint.getPos(render)
        return p

    sprayTrack = MovieUtil.getSprayTrack(battle, WaterSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                         dSprayHold, dSprayScale, horizScale=scale, vertScale=scale)
    pistolPos = Point3(0.28, 0.1, 0.08)
    pistolHpr = VBase3(85.6, -4.44, 94.43)
    pistolTrack = Sequence(Func(MovieUtil.showProp, pistol, handJointPath0, pistolPos, pistolHpr),
                           LerpScaleInterval(pistol, dPistolScale, pistol.getScale(),
                                             startScale=MovieUtil.PNT3_NEARZERO), Wait(tSpray - dPistolScale))
    pistolTrack.append(sprayTrack)
    pistolTrack.append(Wait(dPistolHold))
    pistolTrack.append(LerpScaleInterval(pistol, dPistolScale, MovieUtil.PNT3_NEARZERO))
    pistolTrack.append(Func(handJoinPath1.removeNode))
    pistolTrack.append(Func(handJointPath0.removeNode))
    pistolTrack.append(Func(MovieUtil.removeProp, pistol))
    tracks.append(pistolTrack)
    if hp > 0:
        tracks.append(__getSplashTrack(targetPoint, scale, tSpray + dSprayScale, battle))
    if hp > 0 or delay <= 0:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'squirt-small-react', died, leftSuits,
                           rightSuits, battle, fShowStun, attackLevel=2, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doWaterBalloon(squirt, delay, fShowStun):
    toon = squirt['toon']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    sidestep = squirt['sidestep']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    level = squirt['level']
    battle = squirt['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    balloonName = pieNames[8]
    hitSuit = hp > 0
    scale = sprayScales[level]
    tWindUp = 1.7
    tLaunch = tWindUp + 0.9
    tContact = tLaunch + 0.3
    tSuitDodges = max(tContact - 0.7, 0.0)
    balloon = globalPropPool.getProp(balloonName)
    balloon.setColor(0.2, 1, 0.4, 1)
    balloon.setScale(1.2, 1.2, 0.8)
    balloon2 = MovieUtil.copyProp(balloon)
    balloons = [balloon, balloon2]
    hands = toon.getRightHands()
    tracks = Parallel()
    toonTrack = Sequence()
    toonFace = Func(toon.headsUp, battle, suitPos)
    toonTrack.append(Wait(delay))
    toonTrack.append(toonFace)
    toonTrack.append(ActorInterval(toon, 'throw'))
    toonTrack.append(Func(toon.loop, 'neutral'))
    toonTrack.append(Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    balloonShow = Func(MovieUtil.showProps, balloons, hands)
    balloonScale1 = LerpScaleInterval(balloon, 1.0, balloon.getScale(), startScale=MovieUtil.PNT3_NEARZERO)
    balloonScale2 = LerpScaleInterval(balloon2, 1.0, balloon2.getScale(), startScale=MovieUtil.PNT3_NEARZERO)
    balloonScale = Parallel(balloonScale1, balloonScale2)
    balloonPreflight = Func(MovieThrow.__propPreflight, balloons, suit, toon, battle)
    balloonTrack = Sequence(Wait(delay), balloonShow, balloonScale,
                            Func(battle.movie.needRestoreRenderProp, balloons[0]), Wait(tLaunch - 1.0),
                            balloonPreflight)

    targetPoint = __suitTargetPoint(suit)

    soundThrow = Sequence(Wait(2.6), SoundInterval(globalBattleSoundCache.getSound('AA_pie_throw_only.ogg'), node=toon))
    soundSplash = __getSoundTrack(level, hitSuit, tContact, toon)
    soundTracks = Parallel(soundThrow, soundSplash)
    tracks.append(soundTracks)

    if hitSuit:
        pieFly = LerpPosInterval(balloon, tContact - tLaunch, pos=MovieUtil.avatarFacePoint(suit, other=battle),
                                 name=MovieThrow.pieFlyTaskName, other=battle)
        pieHide = Func(MovieUtil.removeProps, balloons)
        balloonTrack.append(pieFly)
        balloonTrack.append(pieHide)
        balloonTrack.append(Func(battle.movie.clearRenderProp, balloons[0]))

    else:
        missDict = {}
        if sidestep:
            suitPoint = MovieUtil.avatarFacePoint(suit, other=battle)
        else:
            suitPoint = MovieThrow.__suitMissPoint(suit, other=battle)
        piePreMiss = Func(MovieThrow.__piePreMiss, missDict, balloon, suitPoint, battle)
        pieMiss = LerpFunctionInterval(MovieThrow.__pieMissLerpCallback, extraArgs=[missDict],
                                       duration=(tContact - tLaunch) * ratioMissToHit)
        pieHide = Func(MovieUtil.removeProps, balloons)
        balloonTrack.append(piePreMiss)
        balloonTrack.append(pieMiss)
        balloonTrack.append(pieHide)
        balloonTrack.append(Func(battle.movie.clearRenderProp, balloons[0]))
    tracks.append(balloonTrack)

    if hp > 0:
        tracks.append(__getSplashTrack(targetPoint, scale, tContact, battle))
    if hp > 0 or delay <= 0:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'squirt-small-react', died, leftSuits,
                           rightSuits, battle, fShowStun, attackLevel=3, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doSeltzerBottle(squirt, delay, fShowStun):
    toon = squirt['toon']
    level = squirt['level']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    battle = squirt['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    hitSuit = hp > 0
    scale = sprayScales[level]
    dBottleScale = 0.5
    dBottleHold = 3.0
    tSpray = 53.0 / toon.getFrameRate('hold-bottle') + 0.05
    dSprayScale = 0.2
    dSprayHold = 0.1
    tContact = tSpray + dSprayScale
    tSuitDodges = max(tContact - 0.7, 0.0)
    tracks = Parallel()
    toonTrack = Sequence(Func(toon.headsUp, battle, suitPos), ActorInterval(toon, 'hold-bottle'),
                         Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    soundTrack = __getSoundTrack(level, hitSuit, tSpray - dSprayHold, toon)
    tracks.append(soundTrack)
    bottle = globalPropPool.getProp('bottle')
    hands = toon.getRightHands()
    targetPoint = __suitTargetPoint(suit)

    def getSprayStartPos():
        toon.update(0)
        joint = bottle.find('**/joint_toSpray')
        n = hidden.attachNewNode('pointBehindSprayProp')
        n.reparentTo(toon)
        n.setPos(joint.getPos(toon) + Point3(0, -0.4, 0))
        p = n.getPos(render)
        n.removeNode()
        del n
        return p

    sprayTrack = MovieUtil.getSprayTrack(battle, WaterSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                         dSprayHold, dSprayScale, horizScale=scale, vertScale=scale)
    handJoinPath0 = hands[0].attachNewNode('handJoint0-path')
    handJointPath1 = handJoinPath0.instanceTo(hands[1])
    bottleTrack = Sequence(Func(MovieUtil.showProp, bottle, handJoinPath0),
                           LerpScaleInterval(bottle, dBottleScale, bottle.getScale(),
                                             startScale=MovieUtil.PNT3_NEARZERO), Wait(tSpray - dBottleScale))
    bottleTrack.append(sprayTrack)
    bottleTrack.append(Wait(dBottleHold))
    bottleTrack.append(LerpScaleInterval(bottle, dBottleScale, MovieUtil.PNT3_NEARZERO))
    bottleTrack.append(Func(handJointPath1.removeNode))
    bottleTrack.append(Func(handJoinPath0.removeNode))
    bottleTrack.append(Func(MovieUtil.removeProp, bottle))
    tracks.append(bottleTrack)
    if hp > 0:
        tracks.append(__getSplashTrack(targetPoint, scale, tSpray + dSprayScale, battle))
    if (hp > 0 or delay <= 0) and suit:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'squirt-small-react', died, leftSuits,
                           rightSuits, battle, fShowStun, attackLevel=4, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doFireHose(squirt, delay, fShowStun):
    toon = squirt['toon']
    level = squirt['level']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    battle = squirt['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    hitSuit = hp > 0
    scale = 0.3
    tAppearDelay = 0.7
    dHoseHold = 0.7
    dAnimHold = 5.1
    tSprayDelay = 2.8
    dSprayScale = 0.1
    dSprayHold = 1.8
    tContact = 2.9
    tSuitDodges = 2.1
    tracks = Parallel()
    toonTrack = Sequence(Wait(tAppearDelay), Func(toon.headsUp, battle, suitPos), ActorInterval(toon, 'firehose'),
                         Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    soundTrack = __getSoundTrack(level, hitSuit, tSprayDelay, toon)
    tracks.append(soundTrack)
    hose = globalPropPool.getProp('firehose')
    hydrant = globalPropPool.getProp('hydrant')
    hose.reparentTo(hydrant)
    (hose.pose('firehose', 2),)
    hydrantNode = toon.attachNewNode('hydrantNode')
    hydrantNode.clearTransform(toon.getGeomNode().getChild(0))
    hydrantScale = hydrantNode.attachNewNode('hydrantScale')
    hydrant.reparentTo(hydrantScale)
    toon.pose('firehose', 30)
    toon.update(0)
    torso = toon.getPart('torso', '1000')
    if toon.style.torso[0] == 'm':
        hydrant.setPos(torso, 0, 0, -1.85)
    else:
        hydrant.setPos(torso, 0, 0, -1.45)
    hydrant.setPos(0, 0, hydrant.getZ())
    base = hydrant.find('**/base')
    base.setColor(1, 1, 1, 0.5)
    base.setPos(toon, 0, 0, 0)
    toon.loop('neutral')
    targetPoint = __suitTargetPoint(suit)

    def getSprayStartPos():
        toon.update(0)
        if hose.isEmpty() == 1:
            if callable(targetPoint):
                return targetPoint()
            else:
                return targetPoint
        joint = hose.find('**/joint_water_stream')
        n = hidden.attachNewNode('pointBehindSprayProp')
        n.reparentTo(toon)
        n.setPos(joint.getPos(toon) + Point3(0, -0.55, 0))
        p = n.getPos(render)
        n.removeNode()
        del n
        return p

    sprayTrack = Sequence()
    sprayTrack.append(Wait(tSprayDelay))
    sprayTrack.append(
        MovieUtil.getSprayTrack(battle, WaterSprayColor, getSprayStartPos, targetPoint, dSprayScale, dSprayHold,
                                dSprayScale, horizScale=scale, vertScale=scale))
    tracks.append(sprayTrack)
    hydrantNode.detachNode()
    propTrack = Sequence(Func(battle.movie.needRestoreRenderProp, hydrantNode), Func(hydrantNode.reparentTo, toon),
                         LerpScaleInterval(hydrantScale, tAppearDelay * 0.5, Point3(1, 1, 1.4),
                                           startScale=Point3(1, 1, 0.01)),
                         LerpScaleInterval(hydrantScale, tAppearDelay * 0.3, Point3(1, 1, 0.8),
                                           startScale=Point3(1, 1, 1.4)),
                         LerpScaleInterval(hydrantScale, tAppearDelay * 0.1, Point3(1, 1, 1.2),
                                           startScale=Point3(1, 1, 0.8)),
                         LerpScaleInterval(hydrantScale, tAppearDelay * 0.1, Point3(1, 1, 1),
                                           startScale=Point3(1, 1, 1.2)),
                         ActorInterval(hose, 'firehose', duration=dAnimHold), Wait(dHoseHold - 0.2),
                         LerpScaleInterval(hydrantScale, 0.2, Point3(1, 1, 0.01), startScale=Point3(1, 1, 1)),
                         Func(MovieUtil.removeProps, [hydrantNode, hose]),
                         Func(battle.movie.clearRenderProp, hydrantNode))
    tracks.append(propTrack)
    if hp > 0:
        tracks.append(__getSplashTrack(targetPoint, 0.4, 2.7, battle, splashHold=1.5))
    if hp > 0 or delay <= 0:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'squirt-small-react', died, leftSuits,
                           rightSuits, battle, fShowStun, attackLevel=5, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doStormCloud(squirt, delay, fShowStun):
    toon = squirt['toon']
    level = squirt['level']
    target = squirt['target']
    suit = target['suit']
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    battle = squirt['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    hitSuit = hp > 0
    tContact = 2.9
    tSuitDodges = 1.8
    tracks = Parallel()
    soundTrack = __getSoundTrack(level, hitSuit, 2.3, toon)
    soundTrack2 = __getSoundTrack(level, hitSuit, 4.6, toon)
    tracks.append(soundTrack)
    tracks.append(soundTrack2)
    button = globalPropPool.getProp('button')
    button2 = MovieUtil.copyProp(button)
    buttons = [button, button2]
    hands = toon.getLeftHands()
    toonTrack = Sequence(Func(MovieUtil.showProps, buttons, hands), Func(toon.headsUp, battle, suitPos),
                         ActorInterval(toon, 'pushbutton'), Func(MovieUtil.removeProps, buttons),
                         Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    cloud = globalPropPool.getProp('stormcloud')
    BattleParticles.loadParticles()
    trickleEffect = BattleParticles.createParticleEffect(file='trickleLiquidate')
    rainEffect = BattleParticles.createParticleEffect(file='liquidate')
    rainEffect2 = BattleParticles.createParticleEffect(file='liquidate')
    rainEffect3 = BattleParticles.createParticleEffect(file='liquidate')
    cloudHeight = suit.height + 3
    cloudPosPoint = Point3(0, 0, cloudHeight)
    scaleUpPoint = Point3(3, 3, 3)
    rainEffects = [rainEffect, rainEffect2, rainEffect3]
    rainDelay = 1
    effectDelay = 0.3
    if hp > 0:
        cloudHold = 4.7
    else:
        cloudHold = 1.7

    def getCloudTrack(useEffect):
        track = Sequence(Func(MovieUtil.showProp, cloud, suit, cloudPosPoint), Func(cloud.pose, 'stormcloud', 0),
                         LerpScaleInterval(cloud, 1.5, scaleUpPoint, startScale=MovieUtil.PNT3_NEARZERO),
                         Wait(rainDelay))
        if useEffect:
            parallelTrack = Parallel()
            trickleDelay = trickleDuration = cloudHold * 0.25
            trickleTrack = Sequence(Func(battle.movie.needRestoreParticleEffect, trickleEffect),
                                    ParticleInterval(trickleEffect, cloud, worldRelative=False,
                                                     duration=trickleDuration, cleanup=True),
                                    Func(battle.movie.clearRestoreParticleEffect, trickleEffect))
            track.append(trickleTrack)
            for i in xrange(0, 3):
                dur = cloudHold - 2 * trickleDuration
                parallelTrack.append(Sequence(Func(battle.movie.needRestoreParticleEffect, rainEffects[i]),
                                              Wait(trickleDelay),
                                              ParticleInterval(rainEffects[i], cloud, worldRelative=False,
                                                               duration=dur, cleanup=True),
                                              Func(battle.movie.clearRestoreParticleEffect, rainEffects[i])))
                trickleDelay += effectDelay

            parallelTrack.append(Sequence(Wait(3 * effectDelay),
                                          ActorInterval(cloud, 'stormcloud', startTime=1, duration=cloudHold)))
            track.append(parallelTrack)
        else:
            track.append(ActorInterval(cloud, 'stormcloud', startTime=1, duration=cloudHold))
        track.append(LerpScaleInterval(cloud, 0.5, MovieUtil.PNT3_NEARZERO))
        track.append(Func(MovieUtil.removeProp, cloud))
        return track

    tracks.append(getCloudTrack(1))
    tracks.append(getCloudTrack(0))
    if hp > 0 or delay <= 0:
        tracks.append(
            __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'soak', died, leftSuits, rightSuits,
                           battle, fShowStun, beforeStun=2.6, afterStun=2.3, attackLevel=6, revived=revived,
                           prest=toon.checkTrackPrestige(SQUIRT_TRACK)))
    return tracks


def __doGeyser(squirt, delay, fShowStun, uberClone=0):
    toon = squirt['toon']
    level = squirt['level']
    tracks = Parallel()
    tContact = 2.9
    tSuitDodges = 1.8
    button = globalPropPool.getProp('button')
    button2 = MovieUtil.copyProp(button)
    buttons = [button, button2]
    hands = toon.getLeftHands()
    battle = squirt['battle']
    origHpr = toon.getHpr(battle)
    target = squirt['target']
    suit = target['suit']
    suitPos = suit.getPos(battle)
    toonTrack = Sequence(Func(MovieUtil.showProps, buttons, hands), Func(toon.headsUp, battle, suitPos),
                         ActorInterval(toon, 'pushbutton'), Func(MovieUtil.removeProps, buttons),
                         Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    hp = target['hp']
    hpBonus = target['hpBonus']
    kbBonus = target['kbBonus']
    died = target['died']
    revived = target['revived']
    leftSuits = target['leftSuits']
    rightSuits = target['rightSuits']
    hitSuit = hp > 0
    soundTrack = __getSoundTrack(level, hitSuit, 1.8, toon)
    delayTime = random.random()
    tracks.append(Wait(delayTime))
    tracks.append(soundTrack)
    cloud = globalPropPool.getProp('geyser')
    BattleParticles.loadParticles()
    scaleUpPoint = Point3(1.8, 1.8, 1.8)
    rainDelay = 2.5
    if hp > 0:
        geyserHold = 1.5
    else:
        geyserHold = 0.5

    def getGeyserTrack(geyser):
        geyserMound = MovieUtil.copyProp(geyser)
        geyserRemoveM = geyserMound.findAllMatches('**/Splash*')
        geyserRemoveM.addPathsFrom(geyserMound.findAllMatches('**/spout'))
        for i in xrange(geyserRemoveM.getNumPaths()):
            geyserRemoveM[i].removeNode()

        geyserWater = MovieUtil.copyProp(geyser)
        geyserRemoveW = geyserWater.findAllMatches('**/hole')
        geyserRemoveW.addPathsFrom(geyserWater.findAllMatches('**/shadow'))
        for i in xrange(geyserRemoveW.getNumPaths()):
            geyserRemoveW[i].removeNode()

        track = Sequence(Wait(rainDelay), Func(MovieUtil.showProp, geyserMound, battle, suit.getPos(battle)),
                         Func(MovieUtil.showProp, geyserWater, battle, suit.getPos(battle)),
                         LerpScaleInterval(geyserWater, 1.0, scaleUpPoint, startScale=MovieUtil.PNT3_NEARZERO),
                         Wait(geyserHold * 0.5),
                         LerpScaleInterval(geyserWater, 0.5, MovieUtil.PNT3_NEARZERO, startScale=scaleUpPoint))
        track.append(LerpScaleInterval(geyserMound, 0.5, MovieUtil.PNT3_NEARZERO))
        track.append(Func(MovieUtil.removeProp, geyserMound))
        track.append(Func(MovieUtil.removeProp, geyserWater))
        track.append(Func(MovieUtil.removeProp, geyser))
        return track

    if not uberClone:
        tracks.append(Sequence(Wait(delayTime), getGeyserTrack(cloud)))
    if hp > 0 or delay <= 0:
        tracks.append(Sequence(Wait(delayTime),
                               __getSuitTrack(suit, tContact, tSuitDodges, hp, hpBonus, kbBonus, 'soak', died,
                                              leftSuits, rightSuits, battle, fShowStun, beforeStun=2.6,
                                              afterStun=2.3, attackLevel=7, uberRepeat=uberClone, revived=revived,
                                              prest=toon.checkTrackPrestige(SQUIRT_TRACK))))

    return tracks


squirtFunctions = (__doFlower,
                   __doWaterGlass,
                   __doWaterGun,
                   __doWaterBalloon,
                   __doSeltzerBottle,
                   __doFireHose,
                   __doStormCloud,
                   __doGeyser)
