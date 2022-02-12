from direct.interval.ActorInterval import ActorInterval
from direct.interval.IntervalGlobal import *
from direct.interval.LerpInterval import LerpPosInterval, LerpScaleInterval
from direct.interval.MetaInterval import Sequence, Parallel

import toontown.battle.movies.BattleParticles
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleProps import globalPropPool
from toontown.suit.SuitDNA import getSuitBodyType
from toontown.toonbase import TTLocalizer

notify = DirectNotifyGlobal.directNotify.newCategory('MovieUtil')
SUIT_LOSE_DURATION = 6.0
SUIT_LURE_DISTANCE = 2.6
SUIT_LURE_DOLLAR_DISTANCE = 5.1
SUIT_EXTRA_REACH_DISTANCE = 0.9
SUIT_EXTRA_RAKE_DISTANCE = 1.1
SUIT_TRAP_DISTANCE = 2.6
SUIT_TRAP_RAKE_DISTANCE = 4.5
SUIT_TRAP_MARBLES_DISTANCE = 3.7
SUIT_TRAP_TNT_DISTANCE = 5.1
PNT3_NEARZERO = Point3(0.01, 0.01, 0.01)
PNT3_ZERO = Point3(0.0, 0.0, 0.0)
PNT3_ONE = Point3(1.0, 1.0, 1.0)
largeSuits = ['f',
              'cc',
              'gh',
              'tw',
              'bf',
              'sc',
              'ds',
              'hh',
              'cr',
              'tbc',
              'bs',
              'sd',
              'le',
              'bw',
              'nc',
              'mb',
              'ls',
              'rb',
              'ms',
              'tf',
              'm',
              'mh']
shotDirection = 'left'


def avatarDodge(leftAvatars, rightAvatars, leftData, rightData):
    if len(leftAvatars) > len(rightAvatars):
        PoLR = rightAvatars
        PoMR = leftAvatars
    else:
        PoLR = leftAvatars
        PoMR = rightAvatars
    upper = 1 + 4 * abs(len(leftAvatars) - len(rightAvatars))
    if random.randint(0, upper) > 0:
        avDodgeList = PoLR
    else:
        avDodgeList = PoMR
    if avDodgeList is leftAvatars:
        data = leftData
    else:
        data = rightData
    return avDodgeList, data


def avatarHide(avatar):
    notify.debug('avatarHide(%d)' % avatar.doId)
    if hasattr(avatar, 'battleTrapProp'):
        notify.debug('avatar.battleTrapProp = %s' % avatar.battleTrapProp)
    avatar.detachNode()


def copyProp(prop):
    from direct.actor import Actor
    if isinstance(prop, Actor.Actor):
        return Actor.Actor(other=prop)
    else:
        return prop.copyTo(hidden)


def showProp(prop, hand, pos=None, hpr=None, scale=None):
    prop.reparentTo(hand)
    if pos:
        if callable(pos):
            pos = pos()
        prop.setPos(pos)
    if hpr:
        if callable(hpr):
            hpr = hpr()
        prop.setHpr(hpr)
    if scale:
        if callable(scale):
            scale = scale()
        prop.setScale(scale)


def showProps(props, hands, pos=None, hpr=None, scale=None):
    index = 0
    for prop in props:
        prop.reparentTo(hands[index])
        if pos:
            prop.setPos(pos)
        if hpr:
            prop.setHpr(hpr)
        if scale:
            prop.setScale(scale)
        index += 1


def hideProps(props):
    for prop in props:
        prop.detachNode()


def removeProp(prop):
    from direct.actor import Actor
    if prop.isEmpty() == 1 or not prop:
        return
    prop.detachNode()
    if isinstance(prop, Actor.Actor):
        prop.cleanup()
    else:
        prop.removeNode()
    return


def removeProps(props):
    for prop in props:
        removeProp(prop)


def getActorIntervals(props, anim):
    tracks = Parallel()
    for prop in props:
        tracks.append(ActorInterval(prop, anim))

    return tracks


def getScaleIntervals(props, duration, startScale, endScale):
    tracks = Parallel()
    for prop in props:
        tracks.append(LerpScaleInterval(prop, duration, endScale, startScale=startScale))

    return tracks


def avatarFacePoint(av, other=render):
    pnt = av.getPos(other)
    pnt.setZ(pnt[2] + av.getHeight())
    return pnt


def insertDeathSuit(suit, deathSuit, battle=None, pos=None, hpr=None):
    holdParent = suit.getParent()
    if suit.getVirtual():
        virtualize(deathSuit)
    avatarHide(suit)
    __positionDeathSuit(battle, deathSuit, holdParent, hpr, pos)


def removeDeathSuit(suit, deathSuit):
    notify.debug('removeDeathSuit()')
    if not deathSuit.isEmpty():
        deathSuit.detachNode()
        suit.cleanupLoseActor()


def insertZapSuit(suit, zapSuit, battle=None, pos=None, hpr=None):
    holdParent = suit.getParent()
    if suit.getVirtual():
        virtualize(zapSuit)
    __positionDeathSuit(battle, zapSuit, holdParent, hpr, pos)


def removeZapSuit(suit, zapSuit):
    notify.debug('removeDeathSuit()')
    if not zapSuit.isEmpty():
        zapSuit.detachNode()
        suit.cleanupZapActor()


def insertReviveSuit(suit, deathSuit, battle=None, pos=None, hpr=None):
    holdParent = suit.getParent()
    if suit.getVirtual():
        virtualize(deathSuit)
    suit.hide()
    __positionDeathSuit(battle, deathSuit, holdParent, hpr, pos)


def __positionDeathSuit(battle, deathSuit, holdParent, hpr, pos):
    if deathSuit and not deathSuit.isEmpty():
        if holdParent and 0:
            deathSuit.reparentTo(holdParent)
        else:
            deathSuit.reparentTo(render)
        if battle and pos:
            deathSuit.setPos(battle, pos)
        if battle and hpr:
            deathSuit.setHpr(battle, hpr)


def removeReviveSuit(suit, deathSuit):
    notify.debug('removeDeathSuit()')
    suit.setSkelecog(1)
    suit.show()
    if not deathSuit.isEmpty():
        deathSuit.detachNode()
        suit.cleanupLoseActor()
    suit.healthBar.show()
    suit.reseatHealthBarForSkele()


def virtualize(deathSuit):
    actorNode = deathSuit.find('**/__Actor_modelRoot')
    actorCollection = actorNode.findAllMatches('*')
    for thingIndex in xrange(0, actorCollection.getNumPaths()):
        thing = actorCollection[thingIndex]
        if thing.getName() not in ('joint_attachMeter', 'joint_nameTag', 'def_nameTag'):
            thing.setColorScale(1.0, 0.0, 0.0, 1.0)
            # noinspection PyArgumentList
            thing.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
            thing.setDepthWrite(False)
            thing.setBin('fixed', 1)


def createTrainTrackAppearTrack(dyingSuit, battle):
    retval = Sequence()
    possibleSuits = []
    for suitAttack in battle.movie.suitAttackDicts:
        suit = suitAttack['suit']
        if not suit == dyingSuit:
            if hasattr(suit,
                       'battleTrapProp') and suit.battleTrapProp and suit.battleTrapProp.getName() == 'traintrack':
                possibleSuits.append(suitAttack['suit'])

    closestXDistance = 10000
    closestSuit = None
    for suit in possibleSuits:
        suitPoint, suitHpr = battle.getActorPosHpr(suit)
        xDistance = abs(suitPoint.getX())
        if xDistance < closestXDistance:
            closestSuit = suit
            closestXDistance = xDistance

    if closestSuit and closestSuit.battleTrapProp.isHidden():
        closestSuit.battleTrapProp.setColorScale(1, 1, 1, 0)
        closestSuit.battleTrapProp.show()
        newRelativePos = dyingSuit.battleTrapProp.getPos(closestSuit)
        newHpr = dyingSuit.battleTrapProp.getHpr(closestSuit)
        closestSuit.battleTrapProp.setPos(newRelativePos)
        closestSuit.battleTrapProp.setHpr(newHpr)
        retval.append(LerpColorScaleInterval(closestSuit.battleTrapProp, 3.0, Vec4(1, 1, 1, 1)))
    else:
        notify.debug('could not find closest suit, returning empty sequence')
    return retval


def createSuitReviveTrack(suit, battle, npcToons=None):
    if not npcToons:
        npcToons = []
    suitTrack = Sequence()
    suitPos, suitHpr = battle.getActorPosHpr(suit)
    __removeTrainTrap(battle, suit, suitTrack)
    deathSuit = suit.getLoseActor()
    suitTrack.append(Func(insertReviveSuit, suit, deathSuit, battle, suitPos, suitHpr))
    suitTrack.append(ActorInterval(deathSuit, 'lose', duration=SUIT_LOSE_DURATION))
    suitTrack.append(Func(removeReviveSuit, suit, deathSuit, name='remove-death-suit'))
    suitTrack.append(ActorInterval(suit, 'slip-forward'))
    suitTrack.append(Func(suit.loop, 'neutral'))
    suitTrack.append(Func(suit.setHP, suit.maxHP))
    deathSoundTrack = getDeathSoundtrack(deathSuit)
    gears1Track, gears2MTrack = __deathParticleTracks(battle, suit, suitPos)
    toonMTrack = __toonDuckTracks(battle, npcToons)

    return Parallel(suitTrack, deathSoundTrack, gears1Track, gears2MTrack, toonMTrack)


def createSuitDeathTrack(suit, battle, npcToons=None, headless=False):
    if not npcToons:
        npcToons = []
    suitTrack = Sequence()
    suitPos, suitHpr = battle.getActorPosHpr(suit)
    __removeTrainTrap(battle, suit, suitTrack)
    deathSuit = suit.getLoseActor(headless=headless)
    suitTrack.append(Func(notify.debug, 'before insertDeathSuit'))
    suitTrack.append(Func(insertDeathSuit, suit, deathSuit, battle, suitPos, suitHpr))
    suitTrack.append(Func(notify.debug, 'before actorInterval lose'))
    suitTrack.append(ActorInterval(deathSuit, 'lose', duration=SUIT_LOSE_DURATION))
    suitTrack.append(Func(notify.debug, 'before removeDeathSuit'))
    suitTrack.append(Func(removeDeathSuit, suit, deathSuit, name='remove-death-suit'))
    suitTrack.append(Func(notify.debug, 'after removeDeathSuit'))
    deathSoundTrack = getDeathSoundtrack(deathSuit)
    gears1Track, gears2MTrack = __deathParticleTracks(battle, suit, suitPos)
    toonMTrack = __toonDuckTracks(battle, npcToons)

    return Parallel(suitTrack, deathSoundTrack, gears1Track, gears2MTrack, toonMTrack)


def createSuitWalkOut(suit, battle):
    suitPos, suitHpr = battle.getActorPosHpr(suit)
    deathSuit = suit.getLoseActor()
    suitTrack = Sequence(Func(insertDeathSuit, suit, deathSuit, battle, suitPos, suitHpr),
                         Func(deathSuit.setColorScale, Vec4(0.2, 0.2, 0.2, 1)),
                         ActorInterval(deathSuit, 'lose', startTime=SUIT_LOSE_DURATION + 0.2),
                         Func(removeDeathSuit, suit, deathSuit, name='remove-death-suit'))

    return suitTrack


def __removeTrainTrap(battle, suit, suitTrack):
    if hasattr(suit, 'battleTrapProp') and \
            suit.battleTrapProp and \
            suit.battleTrapProp.getName() == 'traintrack' and \
            not suit.battleTrapProp.isHidden():
        suitTrack.append(createTrainTrackAppearTrack(suit, battle))


def getDeathSoundtrack(deathSuit):
    spinningSound = base.loader.loadSfx('phase_3.5/audio/sfx/Cog_Death.ogg')
    deathSound = base.loader.loadSfx('phase_3.5/audio/sfx/ENC_cogfall_apart.ogg')
    deathSoundTrack = Sequence(Wait(0.8),
                               SoundInterval(spinningSound, duration=1.2, startTime=1.5, volume=0.2, node=deathSuit),
                               SoundInterval(spinningSound, duration=3.0, startTime=0.6, volume=0.8, node=deathSuit),
                               SoundInterval(deathSound, volume=0.32, node=deathSuit))
    return deathSoundTrack


def __deathParticleTracks(battle, suit, suitPos, explosionDelay=5.4):
    toontown.battle.movies.BattleParticles.loadParticles()
    gearPoint = Point3(suitPos.getX(), suitPos.getY(), suitPos.getZ() + suit.height - 0.2)
    smallGears = toontown.battle.movies.BattleParticles.createParticleEffect(file='gearExplosionSmall')
    smallGears.setPos(gearPoint)
    smallGears.setDepthWrite(False)
    gears1Track = Sequence(Wait(2.1), ParticleInterval(smallGears, battle, worldRelative=False,
                                                       duration=4.3, cleanup=True), name='gears1Track')
    explosionTrack = Sequence()
    explosionTrack.append(Wait(explosionDelay))
    explosionTrack.append(createKapowExplosionTrack(battle, explosionPoint=gearPoint))
    bigGearExplosion, singleGear, smallGearExplosion = getExplosionGears(gearPoint)
    gears2MTrack = Track((0.0, explosionTrack),
                         (0.7, ParticleInterval(singleGear, battle, worldRelative=False,
                                                duration=5.7, cleanup=True)),
                         (5.2, ParticleInterval(smallGearExplosion, battle, worldRelative=False,
                                                duration=1.2, cleanup=True)),
                         (5.4, ParticleInterval(bigGearExplosion, battle, worldRelative=False,
                                                duration=1.0, cleanup=True)),
                         name='gears2MTrack')
    return gears1Track, gears2MTrack


def spawnHeadExplodeTrack(suit, battle):
    headParts = suit.getHeadParts()
    suitTrack = Sequence()
    suitPos, suitHpr = battle.getActorPosHpr(suit)
    suitTrack.append(Wait(0.15))
    explodeTrack = Parallel()
    for part in headParts:
        explodeTrack.append(Func(part.detachNode))
    suitTrack.append(explodeTrack)
    deathSound = base.loader.loadSfx('phase_3.5/audio/sfx/ENC_cogfall_apart.ogg')
    deathSoundTrack = Sequence(SoundInterval(deathSound, volume=0.8))
    toontown.battle.movies.BattleParticles.loadParticles()
    gearPoint = Point3(suitPos.getX(), suitPos.getY(), suitPos.getZ() + suit.height + 1)
    smallGears = toontown.battle.movies.BattleParticles.createParticleEffect(file='gearExplosionSmall')
    smallGears.setPos(gearPoint)
    smallGears.setDepthWrite(False)
    gears1Track = Sequence(Wait(0.5),
                           ParticleInterval(smallGears, battle, worldRelative=False, duration=1.0, cleanup=True),
                           name='gears1Track')
    explosionTrack = Sequence()
    explosionTrack.append(createKapowExplosionTrack(battle, explosionPoint=gearPoint))
    bigGearExplosion, singleGear, smallGearExplosion = getExplosionGears(gearPoint)
    gears2MTrack = createShortExplosionInterval(battle, bigGearExplosion, singleGear, smallGearExplosion)

    return Parallel(suitTrack, explosionTrack, deathSoundTrack, gears1Track, gears2MTrack)


def getExplosionGears(gearPoint):
    singleGear = toontown.battle.movies.BattleParticles.createParticleEffect('GearExplosion', numParticles=1)
    singleGear.setPos(gearPoint)
    singleGear.setDepthWrite(False)
    smallGearExplosion = toontown.battle.movies.BattleParticles.createParticleEffect('GearExplosion', numParticles=10)
    smallGearExplosion.setPos(gearPoint)
    smallGearExplosion.setDepthWrite(False)
    bigGearExplosion = toontown.battle.movies.BattleParticles.createParticleEffect('BigGearExplosion', numParticles=30)
    bigGearExplosion.setPos(gearPoint)
    bigGearExplosion.setDepthWrite(False)
    return bigGearExplosion, singleGear, smallGearExplosion


def createShortExplosionInterval(battle, bigGearExplosion, singleGear, smallGearExplosion):
    gears2MTrack = Track(
        (0.1, ParticleInterval(singleGear, battle, worldRelative=False, duration=0.4, cleanup=True)),
        (0.5, ParticleInterval(smallGearExplosion, battle, worldRelative=False, duration=0.5, cleanup=True)),
        (0.9, ParticleInterval(bigGearExplosion, battle, worldRelative=False, duration=2.0, cleanup=True)),
        name='gears2MTrack'
    )
    return gears2MTrack


def __toonDuckTracks(battle, npcToons):
    toonMTrack = Parallel(name='toonMTrack')
    for toon in battle.toons:
        toonMTrack.append(Sequence(Wait(1.0), ActorInterval(toon, 'duck'), ActorInterval(toon, 'duck', startTime=1.8),
                                   Func(toon.loop, 'neutral')))
    for toon in npcToons:
        toonMTrack.append(Sequence(Wait(1.0), ActorInterval(toon, 'duck'), ActorInterval(toon, 'duck', startTime=1.8),
                                   Func(toon.loop, 'neutral')))
    return toonMTrack


def createSuitDodgeMultitrack(tDodge, suit, leftSuits, rightSuits):
    suitTracks = Parallel()
    suitDodgeList, sidestepAnim = avatarDodge(leftSuits, rightSuits, 'sidestep-left', 'sidestep-right')
    for s in suitDodgeList:
        suitTracks.append(Sequence(ActorInterval(s, sidestepAnim), Func(s.doNeutralAnim)))

    suitTracks.append(Sequence(ActorInterval(suit, sidestepAnim), Func(suit.doNeutralAnim)))
    suitTracks.append(Func(indicateMissed, suit))
    return Sequence(Wait(tDodge), suitTracks)


def createToonDodgeMultitrack(tDodge, toon, leftToons, rightToons):
    toonTracks = Parallel()
    toonDodgeList, sidestepAnim = avatarDodge(leftToons, rightToons, 'sidestep-left', 'sidestep-right')

    for toonDodge in toonDodgeList:
        toonTracks.append(Sequence(ActorInterval(toonDodge, sidestepAnim), Func(toonDodge.loop, 'neutral')))

    toonTracks.append(Func(indicateMissed, toon))
    return Sequence(Wait(tDodge), toonTracks)


def createSuitTeaseMultiTrack(suit, delay=0.01):
    suitTrack = Sequence(Wait(delay), ActorInterval(suit, 'victory', startTime=0.5, endTime=1.9),
                         Func(suit.doNeutralAnim))
    missedTrack = Sequence(Wait(delay + 0.2), Func(indicateMissed, suit, 0.9))
    return Parallel(suitTrack, missedTrack)


SPRAY_LEN = 1.5


def getSprayTrack(battle, color, origin, target, dScaleUp, dHold, dScaleDown,
                  horizScale=1.0, vertScale=1.0, parent=render):
    track = Sequence()
    sprayProp = globalPropPool.getProp('spray')
    sprayScale = hidden.attachNewNode('spray-parent')
    sprayRot = hidden.attachNewNode('spray-rotate')
    spray = sprayRot
    spray.setColor(color)
    if color[3] < 1.0:
        spray.setTransparency(1)

    def showSpray(sprayOrigin, sprayTarget):
        if callable(sprayOrigin):
            sprayOrigin = sprayOrigin()
        if callable(sprayTarget):
            sprayTarget = sprayTarget()
        sprayRot.reparentTo(parent)
        sprayRot.clearMat()
        sprayScale.reparentTo(sprayRot)
        sprayScale.clearMat()
        sprayProp.reparentTo(sprayScale)
        sprayProp.clearMat()
        sprayRot.setPos(sprayOrigin)
        sprayRot.lookAt(Point3(sprayTarget))

    track.append(Func(battle.movie.needRestoreRenderProp, sprayProp))
    track.append(Func(showSpray, origin, target))

    def calcTargetScale(targetPos=target, targetOrigin=origin):
        if callable(targetPos):
            targetPos = targetPos()
        if callable(targetOrigin):
            targetOrigin = targetOrigin()
        distance = Vec3(targetPos - targetOrigin).length()
        yScale = distance / SPRAY_LEN
        targetScale = Point3(yScale * horizScale, yScale, yScale * vertScale)
        return targetScale

    track.append(LerpScaleInterval(sprayScale, dScaleUp, calcTargetScale, startScale=PNT3_NEARZERO))
    track.append(Wait(dHold))

    def prepareToShrinkSpray(targetPos):
        if callable(targetPos):
            targetPos = targetPos()
        sprayProp.setPos(Point3(0.0, -SPRAY_LEN, 0.0))
        spray.setPos(targetPos)

    track.append(Func(prepareToShrinkSpray, target))
    track.append(LerpScaleInterval(sprayScale, dScaleDown, PNT3_NEARZERO))

    def hideSpray():
        sprayProp.detachNode()
        removeProp(sprayProp)
        sprayRot.removeNode()
        sprayScale.removeNode()

    track.append(Func(hideSpray))
    track.append(Func(battle.movie.clearRenderProp, sprayProp))
    return track


T_HOLE_LEAVES_HAND = 1.708
T_TELEPORT_ANIM = 3.3
T_HOLE_CLOSES = 0.3


def getToonTeleportOutInterval(toon):
    holeActors = toon.getHoleActors()
    holes = [holeActors[0], holeActors[1]]
    hole = holes[0]
    hole2 = holes[1]
    hands = toon.getRightHands()
    delay = T_HOLE_LEAVES_HAND
    dur = T_TELEPORT_ANIM
    holeTrack = Sequence()
    holeTrack.append(Func(showProps, holes, hands))
    (holeTrack.append(Wait(0.5)),)
    holeTrack.append(Func(base.playSfx, toon.getSoundTeleport()))
    holeTrack.append(Wait(delay - 0.5))
    holeTrack.append(Func(hole.reparentTo, toon))
    holeTrack.append(Func(hole2.reparentTo, hidden))
    holeAnimTrack = Sequence()
    holeAnimTrack.append(ActorInterval(hole, 'hole', duration=dur))
    holeAnimTrack.append(Func(hideProps, holes))
    runTrack = Sequence(ActorInterval(toon, 'teleport', duration=dur), Wait(T_HOLE_CLOSES), Func(toon.detachNode))
    return Parallel(runTrack, holeAnimTrack, holeTrack)


def getToonTeleportInInterval(toon):
    hole = toon.getHoleActors()[0]
    holeAnimTrack = Sequence()
    holeAnimTrack.append(Func(toon.detachNode))
    holeAnimTrack.append(Func(hole.reparentTo, toon))
    pos = Point3(0, -2.4, 0)
    holeAnimTrack.append(Func(hole.setPos, toon, pos))
    holeAnimTrack.append(ActorInterval(hole, 'hole', startTime=T_TELEPORT_ANIM, endTime=T_HOLE_LEAVES_HAND))
    holeAnimTrack.append(ActorInterval(hole, 'hole', startTime=T_HOLE_LEAVES_HAND, endTime=T_TELEPORT_ANIM))
    holeAnimTrack.append(Func(hole.reparentTo, hidden))
    delay = T_TELEPORT_ANIM - T_HOLE_LEAVES_HAND
    jumpTrack = Sequence(Wait(delay), Func(toon.reparentTo, render), ActorInterval(toon, 'jump'))
    return Parallel(holeAnimTrack, jumpTrack)


def getSuitStuns(attacks):
    fShowStun = 0
    if isGroupAttack(attacks[0]):
        for target in attacks[0]['target']:
            fShowStun = len(attacks) == 1 and target['hp'] > 0
    else:
        fShowStun = len(attacks) == 1 and attacks[0]['target']['hp'] > 0
    return fShowStun


def isGroupAttack(attack):
    return isinstance(attack['target'], type([]))


def getSuitRakeOffset(suit):
    suitName = suit.getStyleName()
    if suitName == 'gh':
        return 1.4
    elif suitName == 'f':
        return 1.0
    elif suitName == 'cc':
        return 0.7
    elif suitName == 'tw':
        return 1.3
    elif suitName == 'bf':
        return 1.0
    elif suitName == 'sc':
        return 0.8
    elif suitName == 'ym':
        return 0.1
    elif suitName == 'mm':
        return 0.05
    elif suitName == 'tm':
        return 0.07
    elif suitName == 'nd':
        return 0.07
    elif suitName == 'pp':
        return 0.04
    elif suitName == 'bc':
        return 0.36
    elif suitName == 'b':
        return 0.41
    elif suitName == 'dt':
        return 0.31
    elif suitName == 'ac':
        return 0.39
    elif suitName == 'ds':
        return 0.41
    elif suitName == 'hh':
        return 0.8
    elif suitName == 'cr':
        return 2.1
    elif suitName == 'tbc':
        return 1.4
    elif suitName == 'bs':
        return 0.4
    elif suitName == 'sd':
        return 1.02
    elif suitName == 'le':
        return 1.3
    elif suitName == 'bw':
        return 1.4
    elif suitName == 'nc':
        return 0.6
    elif suitName == 'mb':
        return 1.85
    elif suitName == 'ls':
        return 1.4
    elif suitName == 'rb':
        return 1.6
    elif suitName == 'ms':
        return 0.7
    elif suitName == 'tf':
        return 0.75
    elif suitName == 'm':
        return 0.9
    elif suitName == 'mh':
        return 1.3
    else:
        notify.warning('getSuitRakeOffset(suit) - Unknown suit name: %s' % suitName)
        return 0


def startSparksIval(tntProp):
    tip = tntProp.find('**/joint_attachEmitter')
    sparks = toontown.battle.movies.BattleParticles.createParticleEffect(file='tnt')
    return Func(sparks.start, tip)


def startSuitKnockbackInterval(suit, anim, battle):
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
    return Parallel(animTrack, moveTrack)


def indicateMissed(actor, duration=1.1, scale=0.7):
    actor.showHpString(TTLocalizer.AttackMissed, duration=duration, scale=scale)


def createButtonInterval(battle, delay, origHpr, suitPos, toon):
    button = globalPropPool.getProp('button')
    button2 = copyProp(button)
    buttons = [button, button2]
    hands = toon.getLeftHands()
    toonTrack = Sequence(Wait(delay),
                         Func(toon.headsUp, battle, suitPos),
                         ActorInterval(toon, 'pushbutton'),
                         Func(toon.loop, 'neutral'),
                         Func(toon.setHpr, battle, origHpr))
    buttonTrack = Sequence(Wait(delay),
                           Func(showProps, buttons, hands),
                           LerpScaleInterval(button, 1.0, button.getScale(), startScale=Point3(0.01, 0.01, 0.01)),
                           Wait(2.5),
                           LerpScaleInterval(button, 1.0, Point3(0.01, 0.01, 0.01), startScale=button.getScale()),
                           Func(removeProps, buttons))
    return toonTrack, buttonTrack


def createKapowExplosionTrack(parent, explosionPoint=None, scale=1.0):
    explosionTrack = Sequence()
    explosion = loader.loadModel('phase_3.5/models/props/explosion.bam')
    explosion.setBillboardPointEye()
    explosion.setDepthWrite(False)
    if not explosionPoint:
        explosionPoint = Point3(0, 3.6, 2.1)
    explosionTrack.append(Func(explosion.reparentTo, parent))
    explosionTrack.append(Func(explosion.setPos, explosionPoint))
    explosionTrack.append(Func(explosion.setScale, 0.4 * scale))
    explosionTrack.append(Wait(0.6))
    explosionTrack.append(Func(removeProp, explosion))
    return explosionTrack


def createSuitStunInterval(suit, before, after):
    p1 = Point3(0)
    p2 = Point3(0)
    stars = globalPropPool.getProp('stun')
    stars.setColor(1, 1, 1, 1)
    stars.adjustAllPriorities(100)
    head = suit.getHeadParts()[0]
    head.calcTightBounds(p1, p2)
    return Sequence(Wait(before), Func(stars.reparentTo, head), Func(stars.setZ, max(0.0, p2[2] - 1.0)),
                    Func(stars.loop, 'stun'), Wait(after), Func(stars.cleanup), Func(stars.removeNode))


def createSuitResetPosTrack(suit, battle):
    resetPos, resetHpr = battle.getActorPosHpr(suit)
    moveDuration = 0.5
    walkTrack = Sequence(Func(suit.setHpr, battle, resetHpr),
                         ActorInterval(suit, 'walk', startTime=1, duration=moveDuration, endTime=0.0001),
                         Func(suit.loop, 'neutral'))
    moveTrack = LerpPosInterval(suit, moveDuration, resetPos, other=battle)
    return Parallel(walkTrack, moveTrack)


def calcAvgSuitPos(throw):
    battle = throw['battle']
    avgSuitPos = Point3(0, 0, 0)
    numTargets = len(throw['target'])
    for i in xrange(numTargets):
        suit = throw['target'][i]['suit']
        avgSuitPos += suit.getPos(battle)

    avgSuitPos /= numTargets
    return avgSuitPos


def sortAttacks(attacksDict):
    attacks = attacksDict.values()

    def compFunc(a, b):
        if len(a) > len(b):
            return 1
        elif len(a) < len(b):
            return -1
        return 0

    attacks.sort(compFunc)
    return attacks
