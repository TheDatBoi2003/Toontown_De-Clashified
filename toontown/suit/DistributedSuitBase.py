from panda3d.core import *
from libotp import *
from direct.interval.IntervalGlobal import *
from direct.controls.ControlManager import CollisionHandlerRayStart
from direct.task import Task
from otp.otpbase import OTPGlobals
from otp.avatar import DistributedAvatar
import Suit
from toontown.toonbase import ToontownGlobals
from toontown.toonbase import ToontownBattleGlobals
from toontown.toonbase import TTLocalizer
from toontown.battle import SuitBattleGlobals
import SuitTimings
import SuitBase
from direct.directnotify import DirectNotifyGlobal
import SuitDialog
from toontown.battle.movies import BattleProps


class DistributedSuitBase(DistributedAvatar.DistributedAvatar, Suit.Suit, SuitBase.SuitBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedSuitBase')

    def __init__(self, cr):
        try:
            self.DistributedSuitBase_initialized
            return
        except:
            self.DistributedSuitBase_initialized = 1

        DistributedAvatar.DistributedAvatar.__init__(self, cr)
        Suit.Suit.__init__(self)
        SuitBase.SuitBase.__init__(self)
        self.activeShadow = 0
        self.virtual = 0
        self.battleDetectName = None
        self.cRay = None
        self.cRayNode = None
        self.cRayNodePath = None
        self.cRayBitMask = None
        self.lifter = None
        self.cTrav = None
        self.sp = None
        self.fsm = None
        self.prop = None
        self.propInSound = None
        self.propOutSound = None
        self.reparentTo(hidden)
        self.doNeutralAnim(0)
        self.skeleRevives = 0
        self.maxSkeleRevives = 0
        self.sillySurgeText = False
        self.interactivePropTrackBonus = -1
        return

    def setVirtual(self, virtual):
        pass

    def getVirtual(self):
        return 0

    def setSkeleRevives(self, num):
        if num is None:
            num = 0
        self.skeleRevives = num
        if num > self.maxSkeleRevives:
            self.maxSkeleRevives = num
        nameInfo = TTLocalizer.SuitBaseNameWithLevel % {'name': self._name,
                                                        'dept': self.getStyleDept(),
                                                        'level': self.getActualLevel(),
                                                        'exe': self.getExecutiveTitle(),
                                                        'revives': self.getSkeleRevivesTitle()}
        self.setDisplayName(nameInfo)
        return

    def getSkeleRevives(self):
        return self.skeleRevives

    def getMaxSkeleRevives(self):
        return self.maxSkeleRevives

    def getSkeleRevivesTitle(self):
        if self.getSkeleRevives() > 0:
            return ' v%s.0' % (self.getSkeleRevives() + 1)
        else:
            return ''

    def generate(self):
        DistributedAvatar.DistributedAvatar.generate(self)

    def disable(self):
        self.notify.debug('DistributedSuit %d: disabling' % self.getDoId())
        self.ignoreAll()
        self.__removeCollisionData()
        self.cleanupLoseActor()
        self.stop()
        taskMgr.remove(self.uniqueName('blink-task'))
        DistributedAvatar.DistributedAvatar.disable(self)

    def delete(self):
        try:
            self.DistributedSuitBase_deleted
        except:
            self.DistributedSuitBase_deleted = 1
            self.notify.debug('DistributedSuit %d: deleting' % self.getDoId())
            del self.dna
            del self.sp
            DistributedAvatar.DistributedAvatar.delete(self)
            Suit.Suit.delete(self)
            SuitBase.SuitBase.delete(self)

    def setDNAString(self, dnaString):
        Suit.Suit.setDNAString(self, dnaString)

    def setDNA(self, dna):
        Suit.Suit.setDNA(self, dna)

    def getHP(self):
        return self.currHP

    def setHP(self, hp):
        if hp > self.maxHP * self.hardMaxHP:
            self.currHP = self.maxHP * self.hardMaxHP
        else:
            self.currHP = hp
        return None

    def getMaxHP(self):
        return self.maxHP

    def getDialogueArray(self, *args):
        return Suit.Suit.getDialogueArray(self, *args)

    def __removeCollisionData(self):
        self.enableRaycast(0)
        self.cRay = None
        self.cRayNode = None
        self.cRayNodePath = None
        self.lifter = None
        self.cTrav = None
        return

    def setHeight(self, height):
        Suit.Suit.setHeight(self, height)

    def getRadius(self):
        return Suit.Suit.getRadius(self)

    def setLevelDist(self, level):
        if self.notify.getDebug():
            self.notify.debug('Got level %d from server for suit %d' % (level, self.getDoId()))
        self.setLevel(level)

    def attachPropeller(self):
        if not self.prop:
            self.prop = BattleProps.globalPropPool.getProp('propeller')
        if not self.propInSound:
            self.propInSound = base.loader.loadSfx('phase_5/audio/sfx/ENC_propeller_in.ogg')
        if not self.propOutSound:
            self.propOutSound = base.loader.loadSfx('phase_5/audio/sfx/ENC_propeller_out.ogg')
        if base.config.GetBool('want-new-cogs', 0):
            head = self.find('**/to_head')
            if head.isEmpty():
                head = self.find('**/joint_head')
        else:
            head = self.find('**/joint_head')
        self.prop.reparentTo(head)
        return

    def detachPropeller(self):
        if self.prop:
            self.prop.cleanup()
            self.prop.removeNode()
            self.prop = None
        if self.propInSound:
            self.propInSound = None
        if self.propOutSound:
            self.propOutSound = None
        return

    def beginSupaFlyMove(self, pos, moveIn, trackName):
        skyPos = Point3(pos)
        if moveIn:
            skyPos.setZ(pos.getZ() + SuitTimings.fromSky * ToontownGlobals.SuitWalkSpeed)
        else:
            skyPos.setZ(pos.getZ() + SuitTimings.toSky * ToontownGlobals.SuitWalkSpeed)
        groundF = 28
        dur = self.getDuration('landing')
        fr = self.getFrameRate('landing')
        animTimeInAir = groundF / fr
        impactLength = dur - animTimeInAir
        timeTillLanding = SuitTimings.fromSky - impactLength
        waitTime = timeTillLanding - animTimeInAir
        if self.prop is None:
            self.prop = BattleProps.globalPropPool.getProp('propeller')
        propDur = self.prop.getDuration('propeller')
        lastSpinFrame = 8
        fr = self.prop.getFrameRate('propeller')
        spinTime = lastSpinFrame / fr
        openTime = (lastSpinFrame + 1) / fr
        if moveIn:
            lerpPosTrack = Sequence(self.posInterval(timeTillLanding, pos, startPos=skyPos), Wait(impactLength))
            shadowScale = self.dropShadow.getScale()
            shadowTrack = Sequence(Func(self.dropShadow.reparentTo, render), Func(self.dropShadow.setPos, pos),
                                   self.dropShadow.scaleInterval(timeTillLanding, self.scale,
                                                                 startScale=Vec3(0.01, 0.01, 1.0)),
                                   Func(self.dropShadow.reparentTo, self.getShadowJoint()),
                                   Func(self.dropShadow.setPos, 0, 0, 0), Func(self.dropShadow.setScale, shadowScale))
            fadeInTrack = Sequence(Func(self.setTransparency, 1),
                                   self.colorScaleInterval(1, colorScale=VBase4(1, 1, 1, 1),
                                                           startColorScale=VBase4(1, 1, 1, 0)),
                                   Func(self.clearColorScale), Func(self.clearTransparency))
            animTrack = Sequence(Func(self.pose, 'landing', 0), Wait(waitTime),
                                 ActorInterval(self, 'landing', duration=dur), Func(self.loop, 'walk'))
            self.attachPropeller()
            propTrack = Parallel(SoundInterval(self.propInSound, duration=waitTime + dur, node=self), Sequence(
                ActorInterval(self.prop, 'propeller', constrainedLoop=1, duration=waitTime + spinTime, startTime=0.0,
                              endTime=spinTime),
                ActorInterval(self.prop, 'propeller', duration=propDur - openTime, startTime=openTime),
                Func(self.detachPropeller)))
            return Parallel(lerpPosTrack, shadowTrack, fadeInTrack, animTrack, propTrack,
                            name=self.taskName('trackName'))
        else:
            lerpPosTrack = Sequence(Wait(impactLength), LerpPosInterval(self, timeTillLanding, skyPos, startPos=pos))
            shadowTrack = Sequence(Func(self.dropShadow.reparentTo, render), Func(self.dropShadow.setPos, pos),
                                   self.dropShadow.scaleInterval(timeTillLanding, Vec3(0.01, 0.01, 1.0),
                                                                 startScale=self.scale),
                                   Func(self.dropShadow.reparentTo, self.getShadowJoint()),
                                   Func(self.dropShadow.setPos, 0, 0, 0))
            fadeOutTrack = Sequence(Func(self.setTransparency, 1),
                                    self.colorScaleInterval(1, colorScale=VBase4(1, 1, 1, 0),
                                                            startColorScale=VBase4(1, 1, 1, 1)),
                                    Func(self.clearColorScale), Func(self.clearTransparency),
                                    Func(self.reparentTo, hidden))
            actInt = ActorInterval(self, 'landing', loop=0, startTime=dur, endTime=0.0)
            self.attachPropeller()
            self.prop.hide()
            propTrack = Parallel(SoundInterval(self.propOutSound, duration=waitTime + dur, node=self),
                                 Sequence(Func(self.prop.show),
                                          ActorInterval(self.prop, 'propeller', endTime=openTime, startTime=propDur),
                                          ActorInterval(self.prop, 'propeller', constrainedLoop=1,
                                                        duration=propDur - openTime, startTime=spinTime, endTime=0.0),
                                          Func(self.detachPropeller)))
            return Parallel(ParallelEndTogether(lerpPosTrack, shadowTrack, fadeOutTrack), actInt, propTrack,
                            name=self.taskName('trackName'))
        return

    def enableBattleDetect(self, name, handler):
        if self.collTube:
            self.battleDetectName = self.taskName(name)
            self.collNode = CollisionNode(self.battleDetectName)
            self.collNode.addSolid(self.collTube)
            self.collNodePath = self.attachNewNode(self.collNode)
            self.collNode.setCollideMask(ToontownGlobals.WallBitmask)
            self.accept('enter' + self.battleDetectName, handler)
        return Task.done

    def disableBattleDetect(self):
        if self.battleDetectName:
            self.ignore('enter' + self.battleDetectName)
            self.battleDetectName = None
        if self.collNodePath:
            self.collNodePath.removeNode()
            self.collNodePath = None
        return

    def enableRaycast(self, enable=1):
        if not self.cTrav or not hasattr(self, 'cRayNode') or not self.cRayNode:
            return
        self.cTrav.removeCollider(self.cRayNodePath)
        if enable:
            if self.notify.getDebug():
                self.notify.debug('enabling raycast')
            self.cTrav.addCollider(self.cRayNodePath, self.lifter)
        elif self.notify.getDebug():
            self.notify.debug('disabling raycast')

    def b_setBrushOff(self, index):
        self.setBrushOff(index)
        self.d_setBrushOff(index)

    def d_setBrushOff(self, index):
        self.sendUpdate('setBrushOff', [index])

    def setBrushOff(self, index):
        self.setChatAbsolute(SuitDialog.getBrushOffText(self.getStyleName(), index), CFSpeech | CFTimeout)

    def initializeBodyCollisions(self, collIdStr):
        DistributedAvatar.DistributedAvatar.initializeBodyCollisions(self, collIdStr)
        if not self.ghostMode:
            self.collNode.setCollideMask(self.collNode.getIntoCollideMask() | ToontownGlobals.PieBitmask)
        self.cRay = CollisionRay(0.0, 0.0, CollisionHandlerRayStart, 0.0, 0.0, -1.0)
        self.cRayNode = CollisionNode(self.taskName('cRay'))
        self.cRayNode.addSolid(self.cRay)
        self.cRayNodePath = self.attachNewNode(self.cRayNode)
        self.cRayNodePath.hide()
        self.cRayBitMask = ToontownGlobals.FloorBitmask
        self.cRayNode.setFromCollideMask(self.cRayBitMask)
        self.cRayNode.setIntoCollideMask(BitMask32.allOff())
        self.lifter = CollisionHandlerFloor()
        self.lifter.setOffset(ToontownGlobals.FloorOffset)
        self.lifter.setReach(6.0)
        self.lifter.setMaxVelocity(8.0)
        self.lifter.addCollider(self.cRayNodePath, self)
        self.cTrav = base.cTrav

    def disableBodyCollisions(self):
        self.disableBattleDetect()
        self.enableRaycast(0)
        if self.cRayNodePath:
            self.cRayNodePath.removeNode()
        del self.cRayNode
        del self.cRay
        del self.lifter

    def denyBattle(self):
        self.notify.debug('denyBattle()')
        place = self.cr.playGame.getPlace()
        if place.fsm.getCurrentState().getName() == 'WaitForBattle':
            place.setState('walk')
        self.resumePath(self.pathState)

    def makePathTrack(self, nodePath, posPoints, velocity, name):
        track = Sequence(name=name)
        restOfPosPoints = posPoints[1:]
        for pointIndex in xrange(len(posPoints) - 1):
            startPoint = posPoints[pointIndex]
            endPoint = posPoints[pointIndex + 1]
            track.append(Func(nodePath.headsUp, endPoint[0], endPoint[1], endPoint[2]))
            distance = Vec3(endPoint - startPoint).length()
            duration = distance / velocity
            track.append(
                LerpPosInterval(nodePath, duration=duration, pos=Point3(endPoint), startPos=Point3(startPoint)))

        return track

    def setState(self, state):
        if self.fsm is None:
            return 0
        if self.fsm.getCurrentState().getName() == state:
            return 0
        return self.fsm.request(state)

    def subclassManagesParent(self):
        return 0

    def enterOff(self, *args):
        self.hideNametag3d()
        self.hideNametag2d()
        if not self.subclassManagesParent():
            self.setParent(ToontownGlobals.SPHidden)

    def exitOff(self):
        if not self.subclassManagesParent():
            self.setParent(ToontownGlobals.SPRender)
        self.showNametag3d()
        self.showNametag2d()
        self.doNeutralAnim(0)

    def enterBattle(self):
        self.doNeutralAnim(0)
        self.disableBattleDetect()
        self.corpMedallion.hide()
        self.healthBar.show()
        self.updateHealthBar()

    def exitBattle(self):
        self.healthBar.hide()
        self.corpMedallion.show()
        self.currHP = self.maxHP
        self.interactivePropTrackBonus = -1

    def enterWaitForBattle(self):
        self.doNeutralAnim(0)

    def exitWaitForBattle(self):
        pass

    def setSkelecog(self, flag):
        SuitBase.SuitBase.setSkelecog(self, flag)
        if flag:
            Suit.Suit.makeSkeleton(self)

    def setExecutive(self, flag):
        self.notify.debug('Got exe %d from server for suit %d' % (flag, self.getDoId()))
        SuitBase.SuitBase.setExecutive(self, flag)
        if self.isExecutive:
            if not self.isSkelecog:
                self.makeExecutive()
            else:
                self.makeSkeleton()

    def showHpText(self, number, bonus=0, scale=1, attackTrack=-1, attackLevel=-1):
        if self.HpTextEnabled and not self.ghostMode:
            if number != 0:
                if self.hpText:
                    self.hideHpText()
                self.HpTextGenerator.setFont(OTPGlobals.getSignFont())
                if number < 0:
                    hpTextStr = str(number)

                    if attackTrack == ToontownBattleGlobals.SQUIRT_TRACK:
                        hpTextStr += TTLocalizer.StatusSoakRounds % ToontownBattleGlobals.AvSoakRounds[attackLevel]

                    if base.cr.newsManager.isHolidayRunning(ToontownGlobals.SILLY_SURGE_HOLIDAY):
                        self.sillySurgeText = True
                        absNum = abs(number)
                        if 0 < absNum <= 10:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[1]
                        elif 10 < absNum <= 20:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[2]
                        elif 20 < absNum <= 30:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[3]
                        elif 30 < absNum <= 40:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[4]
                        elif 40 < absNum <= 50:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[5]
                        elif 50 < absNum <= 60:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[6]
                        elif 60 < absNum <= 70:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[7]
                        elif 70 < absNum <= 80:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[8]
                        elif 80 < absNum <= 90:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[9]
                        elif 90 < absNum <= 100:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[10]
                        elif 100 < absNum <= 110:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[11]
                        else:
                            hpTextStr += '\n' + TTLocalizer.SillySurgeTerms[12]

                    if self.interactivePropTrackBonus > -1 and self.interactivePropTrackBonus == attackTrack:
                        self.sillySurgeText = True
                        if attackTrack in TTLocalizer.InteractivePropTrackBonusTerms:
                            hpTextStr += '\n' + TTLocalizer.InteractivePropTrackBonusTerms[attackTrack]
                else:
                    hpTextStr = '+' + str(number)

                self.HpTextGenerator.setText(hpTextStr)
                self.HpTextGenerator.clearShadow()
                self.HpTextGenerator.setAlign(TextNode.ACenter)
                if bonus == 1:
                    r = 1.0
                    g = 1.0
                    b = 0
                    a = 1
                elif bonus == 2:
                    r = 1.0
                    g = 0.5
                    b = 0
                    a = 1
                elif number < 0:
                    r = 0.9
                    g = 0
                    b = 0
                    a = 1
                    if self.interactivePropTrackBonus > -1 and self.interactivePropTrackBonus == attackTrack \
                            or attackTrack == ToontownBattleGlobals.SQUIRT_TRACK:
                        r = 0
                        g = 0
                        b = 1
                        a = 1
                else:
                    r = 0
                    g = 0.9
                    b = 0
                    a = 1
                self.HpTextGenerator.setTextColor(r, g, b, a)
                self.hpTextNode = self.HpTextGenerator.generate()
                self.hpText = self.attachNewNode(self.hpTextNode)
                self.hpText.setScale(scale)
                self.hpText.setBillboardPointEye()
                self.hpText.setBin('fixed', 100)
                if self.sillySurgeText:
                    self.nametag3d.setDepthTest(0)
                    self.nametag3d.setBin('fixed', 99)
                self.hpText.setPos(0, 0, self.height / 2)
                seq = Sequence(self.hpText.posInterval(1.0, Point3(0, 0, self.height + 1.5), blendType='easeOut'),
                               Wait(0.85), self.hpText.colorInterval(0.1, Vec4(r, g, b, 0), 0.1), Func(self.hideHpText))
                seq.start()

    def showStatusText(self, statusName, rounds=0, scale=1, attackTrack=-1, attackLevel=-1):
        if self.HpTextEnabled and not self.ghostMode:
            if self.hpText:
                self.hideHpText()
            self.HpTextGenerator.setFont(OTPGlobals.getSignFont())
            textStr = TTLocalizer.StatusNames[SuitBattleGlobals.SuitStatusNames.index(statusName)]
            if rounds:
                textStr += TTLocalizer.StatusRounds % rounds

            self.HpTextGenerator.setText(textStr)
            self.HpTextGenerator.clearShadow()
            self.HpTextGenerator.setAlign(TextNode.ACenter)
            if statusName == SuitBattleGlobals.LURED_STATUS:
                r = 0.1
                g = 0.7
                b = 0.1
                a = 1
            elif statusName == SuitBattleGlobals.SOAKED_STATUS \
                    or statusName == SuitBattleGlobals.DMG_DOWN_STATUS:
                r = 0
                g = 0
                b = 1
                a = 1
            elif statusName == SuitBattleGlobals.SuitStatusNames[2]:
                r = 0.9
                g = 0
                b = 0
                a = 1
            elif statusName == SuitBattleGlobals.SuitStatusNames[4]:
                r = 1.0
                g = 0.5
                b = 0
                a = 1
            else:
                r = 0
                g = 0.9
                b = 0
                a = 1
            self.HpTextGenerator.setTextColor(r, g, b, a)
            self.hpTextNode = self.HpTextGenerator.generate()
            self.hpText = self.attachNewNode(self.hpTextNode)
            self.hpText.setScale(scale)
            self.hpText.setBillboardPointEye()
            self.hpText.setBin('fixed', 100)
            self.hpText.setPos(0, 0, self.height / 2)
            seq = Sequence(self.hpText.posInterval(1.0, Point3(0, 0, self.height + 1.5), blendType='easeOut'),
                           Wait(0.85), self.hpText.colorInterval(0.1, Vec4(r, g, b, 0), 0.1), Func(self.hideHpText))
            seq.start()

    def hideHpText(self):
        DistributedAvatar.DistributedAvatar.hideHpText(self)
        if self.sillySurgeText:
            self.nametag3d.clearDepthTest()
            self.nametag3d.clearBin()
            self.sillySurgeText = False

    def getAvIdName(self):
        try:
            level = self.getActualLevel()
        except:
            level = '???'

        return '%s\n%s\nLevel %s' % (self.getName(), self.doId, level)

    def addStatus(self, statusString):
        SuitBase.SuitBase.addStatus(self, statusString)

    def removeStatus(self, name):
        return SuitBase.SuitBase.removeStatus(self, name)

    def doNeutralAnim(self, restart=1):
        if self.getStatus(SuitBattleGlobals.LURED_STATUS):
            self.loop('lured', restart)
        else:
            self.loop('neutral', restart)
