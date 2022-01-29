from direct.interval.IntervalGlobal import *
from toontown.battle.BattleBase import *
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleSounds import *
from toontown.toon.ToonDNA import *
from toontown.suit.SuitDNA import *
from toontown.battle.movies import MovieUtil
from toontown.battle.movies import MovieNPCSOS
from toontown.battle.movies import MovieCamera
from direct.directnotify import DirectNotifyGlobal
from toontown.battle.movies import BattleParticles

notify = DirectNotifyGlobal.directNotify.newCategory('MovieZap')
hitSoundFiles = ('AA_tesla.ogg', 'AA_carpet.ogg', 'AA_balloon.ogg', 'AA_tesla.ogg',
                 'AA_tesla.ogg', 'AA_tesla.ogg', 'AA_tesla.ogg', 'AA_lightning.ogg')
missSoundFiles = ('AA_tesla_miss.ogg', 'AA_carpet.ogg', 'AA_balloon_miss.ogg', 'AA_tesla_miss.ogg',
                  'AA_tesla_miss.ogg', 'AA_tesla_miss.ogg', 'AA_tesla_miss.ogg', 'AA_lightning_miss.ogg')
sprayScales = [0.2,
               0.3,
               0.1,
               0.6,
               0.8,
               1.0,
               2.0]
ZapSprayColor = Point4(1.0, 1.0, 0, 1.0)
zapPos = Point3(0, 0, 0)
zapHpr = Vec3(0, 0, 0)


def doZaps(zaps):
    if len(zaps) == 0:
        return None, None

    suitZapsDict = {}
    npcArrivals, npcDepartures, npcs = MovieNPCSOS.doNPCTeleports(zaps)
    for zap in zaps:
        skip = 0
        if skip:
            pass
        elif MovieUtil.isGroupAttack(zap):
            target = zap['target'][0]
            suitId = target['suit'].doId
            if suitId in suitZapsDict:
                suitZapsDict[suitId].append(zap)
            else:
                suitZapsDict[suitId] = [zap]
        else:
            suitId = zap['target']['suit'].doId
            if suitId in suitZapsDict:
                suitZapsDict[suitId].append(zap)
            else:
                suitZapsDict[suitId] = [zap]

    suitZaps = MovieUtil.sortAttacks(suitZapsDict)

    delay = 0.0

    mainTrack = Parallel()
    for st in suitZaps:
        if len(st) > 0:
            interval = __doSuitZaps(st, npcs)
            if interval:
                mainTrack.append(Sequence(Wait(delay), interval))
            delay = delay + TOON_ZAP_SUIT_DELAY
    zapTrack = Sequence(npcArrivals, mainTrack, npcDepartures)
    enterDuration = npcArrivals.getDuration()
    exitDuration = npcDepartures.getDuration()
    camDuration = zapTrack.getDuration()
    camTrack = MovieCamera.chooseZapShot(zaps, camDuration, enterDuration, exitDuration)
    return zapTrack, camTrack


def __doSuitZaps(zaps, npcs):
    fShowStun = MovieUtil.getSuitStuns(zaps)

    delay = 0.0
    toonTracks = Parallel()
    for s in zaps:
        tracks = __doZap(s, delay, fShowStun, npcs)
        if tracks:
            for track in tracks:
                toonTracks.append(track)

        delay = delay + TOON_ZAP_DELAY

    return toonTracks


def __doZap(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    zapSequence = Sequence(Wait(delay))
    if MovieUtil.isGroupAttack(zap):
        for target in zap['target']:
            notify.debug('toon: %s zaps prop: %d at suit: %d for hp: %d' % (zap['toon'].getName(),
                                                                            zap['level'],
                                                                            target['suit'].doId,
                                                                            target['hp']))
    else:
        notify.debug('toon: %s zaps prop: %d at suit: %d for hp: %d' % (zap['toon'].getName(),
                                                                        zap['level'],
                                                                        zap['target']['suit'].doId,
                                                                        zap['target']['hp']))
    interval = zap_funcs[zap['level']](zap, delay, fShowStun, npcs=npcs)
    if interval:
        zapSequence.append(interval)
    return [zapSequence]


def __suitTargetPoint(suit):
    pnt = suit.getPos(render)
    pnt.setZ(pnt[2] + suit.getHeight() * 0.66)
    return Point3(pnt)


def __getSuitTrack(suit, tContact, tDodge, hp, anim, died, leftSuits, rightSuits, battle,
                   fShowStun, beforeStun=0.5, afterStun=1.8, revived=0, npcs=None, dodge=False):
    if npcs is None:
        npcs = []
    if hp > 0:
        suitTrack = Sequence(Wait(tContact))
        suitInterval = ActorInterval(suit, anim)
        if fShowStun:
            suitInterval = Parallel(Func(suit.loop, anim), zapCog(suit, beforeStun, afterStun, battle))
        showDamage = Func(suit.showHpText, -hp, openEnded=0, attackTrack=ZAP_TRACK)
        updateHealthBar = Func(suit.updateHealthBar, hp)
        suitTrack.append(showDamage)
        suitTrack.append(updateHealthBar)
        suitTrack.append(suitInterval)
        if died:
            if hp >= suit.maxHP * 2.0 or abs(hp - suit.currHP) <= 5:
                suitTrack.append(shortCircuitTrack(suit, battle))
            else:
                suitTrack.append(MovieUtil.createSuitDeathTrack(suit, battle, npcs))
        else:
            suitTrack.append(Func(suit.loop, 'neutral'))
        if revived:
            suitTrack.append(MovieUtil.createSuitReviveTrack(suit, battle, npcs))
        return suitTrack
    elif dodge:
        return MovieUtil.createSuitDodgeMultitrack(tDodge, suit, leftSuits, rightSuits)
    else:
        return Sequence()


def zapCog(suit, before, after, battle):
    zapSuit = suit.getZapActor()
    zapSuit.setBlend(frameBlend=base.settings.getBool('game', 'interpolate-animations', False))
    suitPos = suit.getPos(battle)
    suitHpr = suit.getHpr(battle)
    zapSuit.setBin("fixed", 0)
    zapSuit.setDepthTest(False)
    zapSuit.setDepthWrite(False)
    zapSfx = loader.loadSfx('phase_5/audio/sfx/AA_cog_shock.ogg')
    p1 = Point3(0)
    p2 = Point3(0)
    head = suit.getHeadParts()[0]
    head.calcTightBounds(p1, p2)
    headLoop = head.hprInterval(0.5, Vec3(360, 0, 0))
    headNormal = head.hprInterval(0, Vec3(0, 0, 0))
    zapTrack = Sequence(Wait(before), Func(base.playSfx, zapSfx), headLoop, headLoop, Wait(after), headNormal)
    flashTrack = Sequence(Wait(before), Func(suit.setColorScale, (0, 0, 0, 1)),
                          Func(MovieUtil.insertZapSuit, suit, zapSuit, battle, suitPos, suitHpr),
                          Func(zapSuit.setColorScale, (1, 1, 0, 1)), Wait(.2),
                          Func(zapSuit.setColorScale, (1, 1, 1, 1)), Wait(.2),
                          Func(zapSuit.setColorScale, (1, 1, 0, 1)), Wait(.2),
                          Func(zapSuit.setColorScale, (1, 1, 1, 1)), Wait(.2),
                          Func(MovieUtil.removeZapSuit, suit, zapSuit),
                          Func(suit.setColorScale, (1, 1, 1, 1)), Wait(after))
    shakeTrack = Sequence(Wait(before), Func(zapSuit.loop, 'shock'), Wait(after))
    return Parallel(zapTrack, flashTrack, shakeTrack)


def shortCircuitTrack(suit, battle):
    if suit.isHidden():
        return Sequence()
    else:
        suitTrack = Sequence()
        suitPos, suitHpr = battle.getActorPosHpr(suit)
        suitTrack.append(Wait(0.15))
        suitTrack.append(Func(MovieUtil.avatarHide, suit))
        deathSound = base.loader.loadSfx('phase_3.5/audio/sfx/ENC_cogfall_apart.ogg')
        deathSoundTrack = Sequence(Wait(0.5), SoundInterval(deathSound, volume=0.8))
        BattleParticles.loadParticles()
        smallGears = BattleParticles.createParticleEffect(file='gearExplosionSmall')
        singleGear = BattleParticles.createParticleEffect('GearExplosion', numParticles=1)
        smallGearExplosion = BattleParticles.createParticleEffect('GearExplosion', numParticles=10)
        bigGearExplosion = BattleParticles.createParticleEffect('BigGearExplosion', numParticles=30)
        gearPoint = Point3(suitPos.getX(), suitPos.getY(), suitPos.getZ() + suit.height - 0.2)
        smallGears.setPos(gearPoint)
        singleGear.setPos(gearPoint)
        smallGears.setDepthWrite(False)
        singleGear.setDepthWrite(False)
        smallGearExplosion.setPos(gearPoint)
        bigGearExplosion.setPos(gearPoint)
        smallGearExplosion.setDepthWrite(False)
        bigGearExplosion.setDepthWrite(False)
        explosionTrack = Sequence()
        explosionTrack.append(MovieUtil.createKapowExplosionTrack(battle, explosionPoint=gearPoint))
        gears1Track = Sequence(Wait(0.5),
                               ParticleInterval(smallGears, battle, worldRelative=False, duration=1.0, cleanup=True),
                               name='gears1Track')
        gears2MTrack = Track(
            (0.1, ParticleInterval(singleGear, battle, worldRelative=False, duration=0.4, cleanup=True)),
            (0.5, ParticleInterval(smallGearExplosion, battle, worldRelative=False, duration=0.5, cleanup=True)),
            (0.9, ParticleInterval(bigGearExplosion, battle, worldRelative=False, duration=2.0, cleanup=True)),
            name='gears2MTrack'
        )

        return Parallel(suitTrack, explosionTrack, deathSoundTrack, gears1Track, gears2MTrack)


def say(statement):
    print statement


def __getSoundTrack(level, hitSuit, delay, node=None):
    if hitSuit:
        soundEffect = globalBattleSoundCache.getSound(hitSoundFiles[level])
    else:
        soundEffect = globalBattleSoundCache.getSound(missSoundFiles[level])
    soundTrack = Sequence()
    if soundEffect:
        if level == 0:
            pass
        else:
            soundTrack.append(Wait(delay))
        soundTrack.append(SoundInterval(soundEffect, node=node))
        return soundTrack


def __doJoybuzzer(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    origPos = toon.getPos(battle)
    runDur = 1
    tCastTime = toon.getDuration('water-gun')
    tWalkUp = 0.9
    tAttack = runDur + tWalkUp
    dReaction = 0.2
    runBackHpr = Vec3(0, 0, 0)
    midPos = Point3(toon.getX(battle) * .5, 0, 0)
    tracks = Parallel()
    button = globalPropPool.getProp('joybuzz')
    button2 = MovieUtil.copyProp(button)
    buttons = [button, button2]
    hands = toon.getRightHands()

    toonTrack = Sequence(Func(MovieUtil.showProps, buttons, hands, Vec3((0.3, 0, 0)), Vec3((-10, -60, 0))),
                         Func(toon.headsUp, battle, suitPos),
                         Func(toon.loop, 'run'), Wait(runDur),
                         ActorInterval(toon, 'water-gun', duration=tCastTime),
                         Func(MovieUtil.removeProps, buttons),
                         Func(toon.setHpr, battle, runBackHpr), Func(toon.loop, 'run'), Wait(runDur), Func(toon.stop),
                         Func(MovieUtil.removeProps, buttons), Func(toon.loop, 'neutral'),
                         Func(toon.setHpr, battle, origHpr))

    tracks.append(toonTrack)

    moveTrack = Sequence(LerpPosInterval(toon, runDur, midPos, other=battle),
                         Wait(tCastTime),
                         LerpPosInterval(toon, runDur, origPos, other=battle))

    tracks.append(moveTrack)

    soundTrack = Sequence(Wait(tAttack), __getSoundTrack(level, hitSuit, tAttack, toon))

    tracks.append(soundTrack)

    suitTrack = Sequence(Wait(runDur), ActorInterval(firstSuit, 'reach', duration=tWalkUp))
    if hitSuit:
        hitTracks = Parallel()
        __getZappedSuitsInterval(battle, fShowStun, dReaction, tAttack, targets, toon, hitTracks)
        suitTrack.append(hitTracks)
    else:
        suitTrack.append(Wait(tCastTime + runDur))
    suitTrack.append(Func(firstSuit.loop, 'neutral'))
    tracks.append(suitTrack)
    return tracks


def __doRug(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    origHpr = toon.getHpr(battle)
    scale = sprayScales[level]
    tSpray = 5.2
    sprayPoseFrame = 88
    dSprayScale = 0.1
    dSprayHold = 0.1
    tContact = tSpray + dSprayScale
    tSuitDodges = max(tSpray - 0.5, 0.0)
    tracks = Parallel()
    tracks.append(ActorInterval(toon, 'run'))
    soundTrack = __getSoundTrack(level, hitSuit, 0, toon)
    tracks.append(soundTrack)
    rug = globalPropPool.getProp('zapRug')
    rugPos = Point3(0, 0, 0.025)
    rugHpr = Point3(0, 0, 0)
    if hitSuit:
        runTrack = Sequence(Func(MovieUtil.showProp, rug, toon, rugPos, rugHpr),
                            ActorInterval(toon, 'walk', playRate=0.7), ActorInterval(toon, 'run'),
                            ActorInterval(toon, 'run', playRate=1.1), ActorInterval(toon, 'run', playRate=1.2),
                            ActorInterval(toon, 'run', playRate=1.3), ActorInterval(toon, 'run', playRate=1.4),
                            ActorInterval(toon, 'water', playRate=1, startFrame=0, endFrame=36), Wait(1),
                            Func(MovieUtil.removeProp, rug), Func(toon.loop, 'neutral'),
                            Func(toon.setHpr, battle, origHpr))
    else:
        runTrack = Sequence(Func(MovieUtil.showProp, rug, toon, rugPos, rugHpr),
                            ActorInterval(toon, 'walk', playRate=0.7), ActorInterval(toon, 'run'),
                            ActorInterval(toon, 'run', playRate=1.1), ActorInterval(toon, 'run', playRate=1.2),
                            ActorInterval(toon, 'run', playRate=1.3), ActorInterval(toon, 'run', playRate=1.4),
                            ActorInterval(toon, 'slip-forward', playRate=1, startFrame=0, endFrame=36), Wait(1),
                            Func(MovieUtil.removeProp, rug), Func(toon.loop, 'neutral'),
                            Func(toon.setHpr, battle, origHpr))
    tracks.append(runTrack)

    targetPoint = __suitTargetPoint(firstSuit)

    def getSprayStartPos(toon=toon):
        toon.update(0)
        lod0 = toon.getLOD(toon.getLODNames()[0])
        if base.config.GetBool('want-new-anims', 1):
            if not lod0.find('**/def_joint_right_hold').isEmpty():
                joint = lod0.find('**/def_joint_right_hold')
            else:
                joint = lod0.find('**/joint_Rhold')
        else:
            joint = lod0.find('**/joint_Rhold')
        p = joint.getPos(render)
        return p

    if hitSuit:
        sprayTrack = MovieUtil.getSprayTrack(battle, ZapSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                             dSprayHold, dSprayScale, horizScale=scale, vertScale=scale)
        tracks.append(Sequence(Wait(tSpray), sprayTrack))
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __doBalloon(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    scale = sprayScales[level]
    dBalloonScale = 3
    dBalloonHold = 1.8
    tSpray = 3
    dSprayScale = 0.1
    dSprayHold = 0.3
    tContact = tSpray + dSprayScale
    tSuitDodges = 1.1
    tracks = Parallel()
    toonTrack = Sequence(Func(toon.headsUp, battle, suitPos), Func(toon.pingpong, 'smooch', fromFrame=40, toFrame=45),
                         Wait(2.5), Func(toon.stop), Func(toon.pingpong, 'cast', fromFrame=30, toFrame=40), Wait(2),
                         Func(toon.stop), Func(toon.loop, 'neutral'), Func(toon.setHpr, battle, origHpr))
    tracks.append(toonTrack)
    soundTrack = __getSoundTrack(level, hitSuit, 0.2, toon)
    tracks.append(soundTrack)
    balloon = globalPropPool.getProp('balloon')
    hands = toon.getRightHands()
    hand_jointpath0 = hands[0].attachNewNode('handJoint0-path')
    hand_jointpath1 = hand_jointpath0.instanceTo(hands[1])

    targetPoint = __suitTargetPoint(firstSuit)

    def getSprayStartPos(pistol=balloon, toon=toon):
        toon.update(0)
        p = pistol.getPos(render)
        return p

    sprayTrack = MovieUtil.getSprayTrack(battle, ZapSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                         dSprayHold, dSprayScale, horizScale=scale, vertScale=scale)
    pistolPos = Point3(0.28, 0.1, 0.08)
    pistolHpr = VBase3(85.6, -4.44, 94.43)
    pistolTrack = Sequence(Func(MovieUtil.showProp, balloon, hand_jointpath0, pistolPos, pistolHpr),
                           LerpScaleInterval(balloon, dBalloonScale, dBalloonScale, startScale=MovieUtil.PNT3_NEARZERO),
                           Wait(tSpray - dBalloonScale))
    pistolTrack.append(sprayTrack)
    pistolTrack.append(Wait(dBalloonHold))
    pistolTrack.append(LerpScaleInterval(balloon, 0.4, MovieUtil.PNT3_NEARZERO, dBalloonScale))
    pistolTrack.append(Func(hand_jointpath1.removeNode))
    pistolTrack.append(Func(hand_jointpath0.removeNode))
    pistolTrack.append(Func(MovieUtil.removeProp, balloon))
    tracks.append(pistolTrack)
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __doBattery(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    origPos = toon.getPos(battle)
    battery = globalPropPool.getProp('battery')
    runBackHpr = Vec3(0, 0, 0)
    hands = toon.getRightHands()
    hand_jointpath0 = hands[0].attachNewNode('handJoint0-path')
    scale = 0.3
    tAppearDelay = 0.7
    midPos = Point3(toon.getX(battle) * .5, 0, 0)
    runDur = 1
    tSprayDelay = 2
    tSpray = 1
    dSprayScale = 0.1
    dSprayHold = 1.8
    tContact = 2
    tSuitDodges = 2.1
    tracks = Parallel()
    toonTrack = Sequence(Wait(tAppearDelay), Func(MovieUtil.showProp, battery, hand_jointpath0),
                         Func(toon.headsUp, battle, suitPos),
                         Func(toon.loop, 'catch-run'), Wait(1), Func(toon.loop, 'catch-neutral'), Wait(3),
                         Func(toon.stop), Func(toon.setHpr, battle, runBackHpr),
                         Func(toon.loop, 'run'), Wait(1), Func(toon.stop), Func(toon.loop, 'catch-run'),
                         Func(toon.loop, 'neutral'), Func(MovieUtil.removeProp, battery),
                         Func(toon.setHpr, battle, origHpr))

    moveTrack = Sequence(Wait(tAppearDelay), LerpPosInterval(toon, runDur, midPos, other=battle), Wait(3),
                         LerpPosInterval(toon, runDur, origPos,
                                         other=battle))

    tracks.append(toonTrack)
    tracks.append(moveTrack)
    soundTrack = __getSoundTrack(level, hitSuit, tSprayDelay, toon)
    tracks.append(soundTrack)

    targetPoint = __suitTargetPoint(firstSuit)

    def getSprayStartPos():
        toon.update(0)
        p = battery.getPos(render)
        return p

    sprayTrack = Sequence()
    sprayTrack.append(Wait(tSprayDelay))
    sprayTrack.append(MovieUtil.getSprayTrack(battle, ZapSprayColor, getSprayStartPos,
                                              targetPoint, dSprayScale, dSprayHold,
                                              dSprayScale, horizScale=scale, vertScale=scale))

    tracks.append(sprayTrack)
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __doTazer(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    origPos = toon.getPos(battle)
    tazer = globalPropPool.getProp('tazer')
    tazer.setHpr(180, 0, 0)
    runBackHpr = Vec3(0, 0, 0)
    hands = toon.getRightHands()
    hand_jointpath0 = hands[0].attachNewNode('handJoint0-path')
    scale = 0.3
    tAppearDelay = 0.7
    midPos = Point3(toon.getX(battle) * .5, 0, 0)
    runDur = 1
    tSprayDelay = 2
    dSprayScale = 0.1
    dSprayHold = 1.8
    tContact = 2
    tSuitDodges = 2.1
    tracks = Parallel()
    toonTrack = Sequence(Wait(tAppearDelay), Func(MovieUtil.showProp, tazer, hand_jointpath0),
                         Func(toon.headsUp, battle, suitPos),
                         Func(toon.loop, 'run'), Wait(1), Func(toon.pingpong, 'cast', fromFrame=30, toFrame=40),
                         Wait(3), Func(toon.stop),
                         Func(toon.setHpr, battle, runBackHpr), Func(toon.loop, 'run'), Wait(1), Func(toon.stop),
                         Func(toon.loop, 'neutral'),
                         Func(MovieUtil.removeProp, tazer), Func(toon.setHpr, battle, origHpr))

    moveTrack = Sequence(Wait(tAppearDelay), LerpPosInterval(toon, runDur, midPos, other=battle), Wait(3),
                         LerpPosInterval(toon, runDur, origPos,
                                         other=battle))

    tracks.append(toonTrack)
    tracks.append(moveTrack)
    soundTrack = __getSoundTrack(level, hitSuit, tSprayDelay, toon)
    tracks.append(soundTrack)

    targetPoint = __suitTargetPoint(firstSuit)

    def getSprayStartPos():
        toon.update(0)
        p = tazer.getPos(render)
        return p

    sprayTrack = Sequence()
    sprayTrack.append(Wait(tSprayDelay))
    sprayTrack.append(
        MovieUtil.getSprayTrack(battle, ZapSprayColor, getSprayStartPos, targetPoint, dSprayScale, dSprayHold,
                                dSprayScale,
                                horizScale=scale, vertScale=scale))

    tracks.append(sprayTrack)
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __doTelevision(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    origPos = toon.getPos(battle)
    battery = globalPropPool.getProp('battery')
    battery.setColor(0.0, 0.0, 0.0, 1.0)
    runBackHpr = Vec3(0, 0, 0)
    hands = toon.getRightHands()
    hand_jointpath0 = hands[0].attachNewNode('handJoint0-path')
    scale = 0.3
    tAppearDelay = 0.7
    midPos = Point3(toon.getX(battle) * .5, 0, 0)
    runDur = 1
    tSprayDelay = 2
    tSpray = 1
    dSprayScale = 0.1
    dSprayHold = 1.8
    tContact = 2
    tSuitDodges = 2.1
    tracks = Parallel()
    toonTrack = Sequence(Wait(tAppearDelay), Func(MovieUtil.showProp, battery, hand_jointpath0),
                         Func(toon.headsUp, battle, suitPos),
                         Func(toon.loop, 'catch-run'), Wait(1), Func(toon.loop, 'catch-neutral'), Wait(3),
                         Func(toon.stop), Func(toon.setHpr, battle, runBackHpr),
                         Func(toon.loop, 'run'), Wait(1), Func(toon.stop), Func(toon.loop, 'catch-run'),
                         Func(toon.loop, 'neutral'), Func(MovieUtil.removeProp, battery),
                         Func(toon.setHpr, battle, origHpr))

    moveTrack = Sequence(Wait(tAppearDelay), LerpPosInterval(toon, runDur, midPos, other=battle), Wait(3),
                         LerpPosInterval(toon, runDur, origPos,
                                         other=battle))

    tracks.append(toonTrack)
    tracks.append(moveTrack)
    soundTrack = __getSoundTrack(level, hitSuit, tSprayDelay, toon)
    tracks.append(soundTrack)

    targetPoint = __suitTargetPoint(firstSuit)

    def getSprayStartPos():
        toon.update(0)
        p = battery.getPos(render)
        return p

    sprayTrack = Sequence()
    sprayTrack.append(Wait(tSprayDelay))
    sprayTrack.append(
        MovieUtil.getSprayTrack(battle, ZapSprayColor, getSprayStartPos, targetPoint, dSprayScale, dSprayHold,
                                dSprayScale,
                                horizScale=scale, vertScale=scale))

    tracks.append(sprayTrack)
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __doTesla(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    origPos = toon.getPos(battle)
    endPos = toon.getPos(battle)
    endPos.setY(endPos.getY() + 3)
    scale = sprayScales[level]
    dSprayScale = 0.1
    dSprayHold = 1.8
    tContact = 2.9
    tSpray = 2.5
    tSuitDodges = 1.8
    shrinkDuration = 0.4
    tracks = Parallel()
    soundTrack = __getSoundTrack(level, hitSuit, 2.3, toon)
    tracks.append(soundTrack)
    toonTrack, buttonTrack = MovieUtil.createButtonInterval(battle, delay, origHpr, suitPos, toon)
    tracks.append(toonTrack)
    tracks.append(buttonTrack)
    coil = globalPropPool.getProp('tesla')
    coil.setPos(endPos)
    propTrack = Sequence()
    propTrack.append(Func(coil.show))
    propTrack.append(Func(coil.setScale, Point3(0.1, 0.1, 0.1)))
    propTrack.append(Func(coil.reparentTo, battle))
    propTrack.append(LerpScaleInterval(coil, 1.5, Point3(1.0, 1.0, 1.0)))
    propTrack.append(Wait(tSpray + 2))
    propTrack.append(LerpScaleInterval(nodePath=coil, scale=Point3(1.0, 1.0, 0.1), duration=shrinkDuration))
    propTrack.append(Func(MovieUtil.removeProp, coil))
    tracks.append(propTrack)

    targetPoint = __suitTargetPoint(firstSuit)

    def getSprayStartPos():
        toon.update(0)
        p = coil.getPos(render)
        p.setZ(5)
        return p

    sprayTrack = Sequence()
    sprayTrack.append(Wait(tSpray))
    sprayTrack.append(MovieUtil.getSprayTrack(battle, ZapSprayColor, getSprayStartPos, targetPoint, dSprayScale,
                                              dSprayHold, dSprayScale, horizScale=scale, vertScale=scale))

    tracks.append(sprayTrack)
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __doLightning(zap, delay, fShowStun, npcs=None):
    if npcs is None:
        npcs = []
    toon = zap['toon']
    battle = zap['battle']
    level = zap['level']
    targets = zap['target']
    firstTarget = targets[zap['order'][0]]
    firstSuit = firstTarget['suit']
    hitSuit = firstTarget['hp'] > 0
    suitPos = firstSuit.getPos(battle)
    origHpr = toon.getHpr(battle)
    if 'npc' in zap:
        toon = zap['npc']
    tracks = Parallel()
    tContact = 1.5
    tSpray = 1.5
    tSuitDodges = 1.8
    toonTrack, buttonTrack = MovieUtil.createButtonInterval(battle, delay, origHpr, suitPos, toon)
    tracks.append(toonTrack)
    tracks.append(buttonTrack)
    soundTrack = __getSoundTrack(level, hitSuit, 2.3, toon)
    tracks.append(soundTrack)
    cloud = globalPropPool.getProp('stormcloud')
    cloudHeight = suit.height + 3
    cloudPosPoint = Point3(0, 0, cloudHeight)
    scaleUpPoint = Point3(10, 10, 10)
    rainDelay = 1
    if hitSuit:
        cloudHold = 4.7
    else:
        cloudHold = 1.7

    def getCloudTrack(cloud, suit, cloudPosPoint, scaleUpPoint, rainDelay, cloudHold, battle=battle):
        tracks = Parallel()
        track = Sequence(Func(MovieUtil.showProp, cloud, suit, cloudPosPoint), Func(cloud.pose, 'stormcloud', 0),
                         LerpScaleInterval(cloud, 1.5, scaleUpPoint, startScale=MovieUtil.PNT3_NEARZERO),
                         Wait(rainDelay), ActorInterval(cloud, 'stormcloud'))
        track.append(LerpScaleInterval(cloud, 0.5, MovieUtil.PNT3_NEARZERO))
        track.append(Func(MovieUtil.removeProp, cloud))
        oldcolor = render.getColorScale()
        lightTrack = Sequence(Wait(rainDelay + 1), LerpColorScaleInterval(render, 1, (0.3, 0.3, 0.3, 1)), Wait(2),
                              LerpColorScaleInterval(render, 1, (oldcolor)))
        tracks.append(track)
        tracks.append(lightTrack)
        return tracks

    tracks.append(getCloudTrack(cloud, firstSuit, cloudPosPoint, scaleUpPoint, rainDelay, cloudHold))
    if hitSuit or delay <= 0:
        __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit)
    return tracks


def __getZappedSuitsInterval(battle, fShowStun, tContact, tSuitDodges, targets, toon, tracks, hitSuit=True):
    for target in targets:
        suit = target['suit']
        hp = target['hp']
        died = target['died']
        revived = target['revived']
        leftSuits = target['leftSuits']
        rightSuits = target['rightSuits']
        tracks.append(__getSuitTrack(suit, tContact, tSuitDodges, hp, 'shock', died, leftSuits, rightSuits,
                                     battle, fShowStun, revived, dodge=not hitSuit))


zap_funcs = (__doJoybuzzer,
             __doRug,
             __doBalloon,
             __doBattery,
             __doTazer,
             __doTelevision,
             __doTesla,
             __doLightning)
