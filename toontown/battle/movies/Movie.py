import copy

from direct.interval.IntervalGlobal import *
from direct.showbase import DirectObject

import toontown.battle.BattleExperience
import MovieDrop
import MovieFire
import MovieHeal
import MovieLure
import MovieNPCSOS
import MoviePetSOS
import MovieSOS
import MovieSound
import MovieSquirt
import MovieSuitAttacks
import MovieThrow
import MovieToonVictory
import MovieTrap
import MovieUtil
import MovieZap
import toontown.battle.movies.PlayByPlayText
import toontown.battle.movies.RewardPanel
from toontown.battle.SuitBattleGlobals import *
from toontown.battle.ToonBattleGlobals import *
from libotp import *
from toontown.battle.BattleBase import *
from toontown.battle.movies import MovieSuitCheats
from toontown.distributed import DelayDelete
from toontown.toon import NPCToons
from toontown.toonbase import ToontownGlobals
from toontown.toonbase.ToontownBattleGlobals import *
from toontown.toontowngui import TTDialog

camPos = Point3(14, 0, 10)
camHpr = Vec3(89, -30, 0)
randomBattleTimestamp = base.config.GetBool('random-battle-timestamp', 0)


class Movie(DirectObject.DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('Movie')

    # noinspection PyMissingConstructor
    def __init__(self, battle):
        self.battle = battle
        self.track = None
        self.rewardPanel = None
        self.rewardCallback = None
        self.playByPlayText = toontown.battle.movies.PlayByPlayText.PlayByPlayText()
        self.playByPlayText.hide()
        self.renderProps = []
        self.hasBeenReset = 0
        self.reset()
        self.rewardHasBeenReset = 0
        self.resetReward()
        return

    def cleanup(self):
        self.reset()
        self.resetReward()
        self.battle = None
        if self.playByPlayText:
            self.playByPlayText.cleanup()
        self.playByPlayText = None
        if self.rewardPanel:
            self.rewardPanel.cleanup()
        self.rewardPanel = None
        self.rewardCallback = None
        return

    def needRestoreColor(self):
        self.restoreColor = 1

    def clearRestoreColor(self):
        self.restoreColor = 0

    def needRestoreHips(self):
        self.restoreHips = 1

    def clearRestoreHips(self):
        self.restoreHips = 0

    def needRestoreHeadScale(self):
        self.restoreHeadScale = 1

    def clearRestoreHeadScale(self):
        self.restoreHeadScale = 0

    def needRestoreToonScale(self):
        self.restoreToonScale = 1

    def clearRestoreToonScale(self):
        self.restoreToonScale = 0

    def needRestoreParticleEffect(self, effect):
        self.specialParticleEffects.append(effect)

    def clearRestoreParticleEffect(self, effect):
        if self.specialParticleEffects.count(effect) > 0:
            self.specialParticleEffects.remove(effect)

    def needRestoreRenderProp(self, prop):
        self.renderProps.append(prop)

    def clearRenderProp(self, prop):
        if self.renderProps.count(prop) > 0:
            self.renderProps.remove(prop)

    def restore(self):
        for toon in self.battle.activeToons:
            toon.loop('neutral')
            origPos, origHpr = self.battle.getActorPosHpr(toon)
            toon.setPosHpr(self.battle, origPos, origHpr)
            hands = toon.getRightHands()[:]
            hands += toon.getLeftHands()
            for hand in hands:
                props = hand.getChildren()
                for prop in props:
                    if prop.getName() != 'book':
                        MovieUtil.removeProp(prop)

            if self.restoreColor == 1:
                headParts = toon.getHeadParts()
                torsoParts = toon.getTorsoParts()
                legsParts = toon.getLegsParts()
                partsList = [headParts, torsoParts, legsParts]
                for parts in partsList:
                    for partNum in xrange(0, parts.getNumPaths()):
                        nextPart = parts.getPath(partNum)
                        nextPart.clearColorScale()
                        nextPart.clearTransparency()

            if self.restoreHips == 1:
                parts = toon.getHipsParts()
                for partNum in xrange(0, parts.getNumPaths()):
                    nextPart = parts.getPath(partNum)
                    props = nextPart.getChildren()
                    for prop in props:
                        if prop.getName() == 'redtape-tube.egg':
                            MovieUtil.removeProp(prop)

            if self.restoreHeadScale == 1:
                headScale = ToontownGlobals.toonHeadScales[toon.style.getAnimal()]
                for lod in toon.getLODNames():
                    toon.getPart('head', lod).setScale(headScale)

            if self.restoreToonScale == 1:
                toon.setScale(1)
            headParts = toon.getHeadParts()
            for partNum in xrange(0, headParts.getNumPaths()):
                part = headParts.getPath(partNum)
                part.setHpr(0, 0, 0)
                part.setPos(0, 0, 0)

            arms = toon.findAllMatches('**/arms')
            sleeves = toon.findAllMatches('**/sleeves')
            hands = toon.findAllMatches('**/hands')
            for partNum in xrange(0, arms.getNumPaths()):
                armPart = arms.getPath(partNum)
                sleevePart = sleeves.getPath(partNum)
                handsPart = hands.getPath(partNum)
                armPart.setHpr(0, 0, 0)
                sleevePart.setHpr(0, 0, 0)
                handsPart.setHpr(0, 0, 0)

        for suit in self.battle.activeSuits:
            if suit._Actor__animControlDict:
                suit.doNeutralAnim(0)
                suit.battleTrapIsFresh = 0
                origPos, origHpr = self.battle.getActorPosHpr(suit)
                suit.setPosHpr(self.battle, origPos, origHpr)
                hands = [suit.getRightHand(), suit.getLeftHand()]
                for hand in hands:
                    props = hand.getChildren()
                    for prop in props:
                        MovieUtil.removeProp(prop)

        for effect in self.specialParticleEffects:
            if effect:
                effect.cleanup()

        self.specialParticleEffects = []
        for prop in self.renderProps:
            MovieUtil.removeProp(prop)

        self.renderProps = []
        return

    def _deleteTrack(self):
        if self.track:
            DelayDelete.cleanupDelayDeletes(self.track)
            self.track = None
        return

    def reset(self, finish=0):
        if self.hasBeenReset == 1:
            return
        self.hasBeenReset = 1
        self.stop()
        self._deleteTrack()
        if finish == 1:
            self.restore()
        self.toonAttackDicts = []
        self.suitPreStatusUpdates = []
        self.suitAttackDicts = []
        self.suitCheatDicts = []
        self.suitPostStatusUpdates = []
        self.restoreColor = 0
        self.restoreHips = 0
        self.restoreHeadScale = 0
        self.restoreToonScale = 0
        self.specialParticleEffects = []
        for prop in self.renderProps:
            MovieUtil.removeProp(prop)

        self.renderProps = []

    def resetReward(self, finish=0):
        if self.rewardHasBeenReset == 1:
            return
        self.rewardHasBeenReset = 1
        self.stop()
        self._deleteTrack()
        if finish == 1:
            self.restore()
        self.toonRewardDicts = []
        if self.rewardPanel:
            self.rewardPanel.destroy()
        self.rewardPanel = None
        return

    def play(self, timestamp, callback):
        self.hasBeenReset = 0
        playTrack = Sequence()
        cameraTrack = Sequence()
        if random.random() > 0.5:
            MovieUtil.shotDirection = 'left'
        else:
            MovieUtil.shotDirection = 'right'
        for s in self.battle.activeSuits:
            s.battleTrapIsFresh = 0

        toonAttacks, toonCam = self.__doToonAttacks()
        if toonAttacks:
            playTrack.append(toonAttacks)
            cameraTrack.append(toonCam)
        suitAttacks, suitCam = self.__doSuitAttacks()
        if suitAttacks:
            playTrack.append(suitAttacks)
            cameraTrack.append(suitCam)

        playTrack.append(Func(callback))
        self._deleteTrack()
        self.track = Sequence(playTrack, name='movie-track-%d' % self.battle.doId)
        if self.battle.localToonPendingOrActive():
            self.track = Parallel(self.track, Sequence(cameraTrack), name='movie-track-with-cam-%d' % self.battle.doId)
        if randomBattleTimestamp == 1:
            randNum = random.randint(0, 99)
            dur = self.track.getDuration()
            timestamp = float(randNum) / 100.0 * dur
        self.track.delayDeletes = []
        for suit in self.battle.suits:
            self.track.delayDeletes.append(DelayDelete.DelayDelete(suit, 'Movie.play'))

        for toon in self.battle.toons:
            self.track.delayDeletes.append(DelayDelete.DelayDelete(toon, 'Movie.play'))

        self.track.start(timestamp)
        return None

    def finish(self):
        self.track.finish()
        return None

    def playReward(self, ts, name, callback, noSkip=False):
        self.rewardHasBeenReset = 0
        playTrack = Sequence()
        cameraTrack = Sequence()
        self.rewardPanel = toontown.battle.movies.RewardPanel.RewardPanel(name)
        self.rewardPanel.hide()
        victory, camVictory, skipper = MovieToonVictory.doToonVictory(self.battle.localToonActive(),
                                                                      self.battle.activeToons, self.toonRewardIds,
                                                                      self.toonRewardDicts, self.deathList,
                                                                      self.rewardPanel, 1, self.helpfulToonsList,
                                                                      noSkip=noSkip)
        if victory:
            skipper.setIvals((playTrack, cameraTrack), playTrack.getDuration())
            playTrack.append(victory)
            cameraTrack.append(camVictory)
        playTrack.append(Func(callback))
        self._deleteTrack()
        self.track = Sequence(playTrack, name='movie-reward-track-%d' % self.battle.doId)
        if self.battle.localToonActive():
            self.track = Parallel(self.track, cameraTrack, name='movie-reward-track-with-cam-%d' % self.battle.doId)
        self.track.delayDeletes = []
        for t in self.battle.activeToons:
            self.track.delayDeletes.append(DelayDelete.DelayDelete(t, 'Movie.playReward'))

        skipper.setIvals((self.track,), 0.0)
        skipper.setBattle(self.battle)
        self.track.start(ts)
        return None

    def playTutorialReward(self, ts, name, callback):
        self.rewardHasBeenReset = 0
        self.rewardPanel = toontown.battle.movies.RewardPanel.RewardPanel(name)
        self.rewardCallback = callback
        self.questList = self.rewardPanel.getQuestIntervalList(base.localAvatar, [0,
                                                                                  1,
                                                                                  1,
                                                                                  0], [base.localAvatar],
                                                               base.localAvatar.quests[0], [],
                                                               [base.localAvatar.getDoId()])
        camera.setPosHpr(0, 8, base.localAvatar.getHeight() * 0.66, 179, 15, 0)
        self.playTutorialReward_1()

    def playTutorialReward_1(self):
        self.tutRewardDialog_1 = TTDialog.TTDialog(text=TTLocalizer.MovieTutorialReward1,
                                                   command=self.playTutorialReward_2, style=TTDialog.Acknowledge,
                                                   fadeScreen=None, pos=(0.65, 0, 0.5), scale=0.8)
        self.tutRewardDialog_1.hide()
        self._deleteTrack()
        self.track = Sequence(name='tutorial-reward-1')
        self.track.append(Func(self.rewardPanel.initGagFrame, base.localAvatar, [0,
                                                                                 0,
                                                                                 0,
                                                                                 0,
                                                                                 0,
                                                                                 0,
                                                                                 0], [0,
                                                                                      0,
                                                                                      0,
                                                                                      0], noSkip=True))
        self.track += self.rewardPanel.getTrackIntervalList(base.localAvatar, THROW, 0, 1)
        self.track.append(Func(self.tutRewardDialog_1.show))
        self.track.start()
        return

    def playTutorialReward_2(self, value):
        self.tutRewardDialog_1.cleanup()
        self.tutRewardDialog_2 = TTDialog.TTDialog(text=TTLocalizer.MovieTutorialReward2,
                                                   command=self.playTutorialReward_3, style=TTDialog.Acknowledge,
                                                   fadeScreen=None, pos=(0.65, 0, 0.5), scale=0.8)
        self.tutRewardDialog_2.hide()
        self._deleteTrack()
        self.track = Sequence(name='tutorial-reward-2')
        self.track.append(Wait(1.0))
        self.track += self.rewardPanel.getTrackIntervalList(base.localAvatar, SQUIRT, 0, 1)
        self.track.append(Func(self.tutRewardDialog_2.show))
        self.track.start()
        return

    def playTutorialReward_3(self, value):
        self.tutRewardDialog_2.cleanup()
        from toontown.toon import Toon
        from toontown.toon import ToonDNA

        def doneChat1(page, elapsed=0):
            self.track2.start()

        def doneChat2(elapsed):
            self.track2.pause()
            self.track3.start()

        def uniqueName(hook):
            return 'TutorialTom-' + hook

        self.tutorialTom = Toon.Toon()
        dna = ToonDNA.ToonDNA()
        dnaList = ('dll', 'ms', 'm', 'm', 7, 0, 7, 7, 2, 6, 2, 6, 2, 16)
        dna.newToonFromProperties(*dnaList)
        self.tutorialTom.setDNA(dna)
        self.tutorialTom.setName(TTLocalizer.NPCToonNames[20000])
        self.tutorialTom.uniqueName = uniqueName
        if base.config.GetString('language', 'english') == 'japanese':
            self.tomDialogue03 = base.loader.loadSfx('phase_3.5/audio/dial/CC_tom_movie_tutorial_reward01.ogg')
            self.tomDialogue04 = base.loader.loadSfx('phase_3.5/audio/dial/CC_tom_movie_tutorial_reward02.ogg')
            self.tomDialogue05 = base.loader.loadSfx('phase_3.5/audio/dial/CC_tom_movie_tutorial_reward03.ogg')
            self.musicVolume = base.config.GetFloat('tutorial-music-volume', 0.5)
        else:
            self.tomDialogue03 = None
            self.tomDialogue04 = None
            self.tomDialogue05 = None
            self.musicVolume = 0.9
        music = base.cr.playGame.place.loader.battleMusic
        if self.questList:
            self.track1 = Sequence(Wait(1.0), Func(self.rewardPanel.initQuestFrame, base.localAvatar,
                                                   copy.deepcopy(base.localAvatar.quests)), Wait(1.0),
                                   Sequence(*self.questList), Wait(1.0), Func(self.rewardPanel.hide),
                                   Func(camera.setPosHpr, render, 34, 19.88, 3.48, -90, -2.36, 0),
                                   Func(base.localAvatar.animFSM.request, 'neutral'),
                                   Func(base.localAvatar.setPosHpr, 40.31, 22.0, -0.47, 150.0, 360.0, 0.0), Wait(0.5),
                                   Func(self.tutorialTom.reparentTo, render), Func(self.tutorialTom.show),
                                   Func(self.tutorialTom.setPosHpr, 40.29, 17.9, -0.47, 11.31, 0.0, 0.07),
                                   Func(self.tutorialTom.animFSM.request, 'TeleportIn'), Wait(1.517),
                                   Func(self.tutorialTom.animFSM.request, 'neutral'),
                                   Func(self.acceptOnce, self.tutorialTom.uniqueName('doneChatPage'), doneChat1),
                                   Func(self.tutorialTom.addActive), Func(music.setVolume, self.musicVolume),
                                   Func(self.tutorialTom.setLocalPageChat, TTLocalizer.MovieTutorialReward3, 0, None,
                                        [self.tomDialogue03]), name='tutorial-reward-3a')
            self.track2 = Sequence(Func(self.acceptOnce, self.tutorialTom.uniqueName('doneChatPage'), doneChat2),
                                   Func(self.tutorialTom.setLocalPageChat, TTLocalizer.MovieTutorialReward4, 1, None,
                                        [self.tomDialogue04]),
                                   Func(self.tutorialTom.setPlayRate, 1.5, 'right-hand-start'),
                                   Func(self.tutorialTom.play, 'right-hand-start'),
                                   Wait(self.tutorialTom.getDuration('right-hand-start') / 1.5),
                                   Func(self.tutorialTom.loop, 'right-hand'), name='tutorial-reward-3b')
            self.track3 = Parallel(Sequence(Func(self.tutorialTom.setPlayRate, -1.8, 'right-hand-start'),
                                            Func(self.tutorialTom.play, 'right-hand-start'),
                                            Wait(self.tutorialTom.getDuration('right-hand-start') / 1.8),
                                            Func(self.tutorialTom.animFSM.request, 'neutral'),
                                            name='tutorial-reward-3ca'), Sequence(Wait(0.5),
                                                                                  Func(self.tutorialTom.setChatAbsolute,
                                                                                       TTLocalizer.MovieTutorialReward5,
                                                                                       CFSpeech | CFTimeout,
                                                                                       self.tomDialogue05), Wait(1.0),
                                                                                  Func(self.tutorialTom.animFSM.request,
                                                                                       'TeleportOut'), Wait(
                    self.tutorialTom.getDuration('teleport')), Wait(1.0), Func(self.playTutorialReward_4, 0),
                                                                                  name='tutorial-reward-3cb'),
                                   name='tutorial-reward-3c')
            self.track1.start()
        else:
            self.playTutorialReward_4(0)
        return

    def playTutorialReward_4(self, value):
        base.localAvatar.setH(270)
        self.tutorialTom.removeActive()
        self.tutorialTom.delete()
        self.questList = None
        self.rewardCallback()
        return

    def stop(self):
        if self.track:
            self.track.finish()
            self._deleteTrack()
        if hasattr(self, 'track1'):
            self.track1.finish()
            self.track1 = None
        if hasattr(self, 'track2'):
            self.track2.finish()
            self.track2 = None
        if hasattr(self, 'track3'):
            self.track3.finish()
            self.track3 = None
        if self.rewardPanel:
            self.rewardPanel.hide()
        if self.playByPlayText:
            self.playByPlayText.hide()
        return

    def __doToonAttacks(self):
        if base.config.GetBool('want-toon-attack-anims', 1):
            track = Sequence(name='toon-attacks')
            camTrack = Sequence(name='toon-attacks-cam')
            interval, cameraInterval = MovieFire.doFires(self.__findToonAttack(FIRE))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieSOS.doSOSs(self.__findToonAttack(SOS))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieNPCSOS.doNPCSOSs(self.__findToonAttack(NPCSOS))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MoviePetSOS.doPetSOSs(self.__findToonAttack(PETSOS))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            hasHealBonus = self.battle.getInteractivePropTrackBonus() == HEAL
            interval, cameraInterval = MovieHeal.doHeals(self.__findToonAttack(HEAL))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieTrap.doTraps(self.__findToonAttack(TRAP))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieLure.doLures(self.__findToonAttack(LURE))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieSound.doSounds(self.__findToonAttack(SOUND))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieSquirt.doSquirts(self.__findToonAttack(SQUIRT))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieZap.doZaps(self.__findToonAttack(ZAP))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieThrow.doThrows(self.__findToonAttack(THROW))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            interval, cameraInterval = MovieDrop.doDrops(self.__findToonAttack(DROP))
            if interval:
                track.append(interval)
                camTrack.append(cameraInterval)
            if len(track) == 0:
                return None, None
            else:
                return track, camTrack
        else:
            return None, None

    def genRewardDicts(self, rewards, deathList, helpfulToonsList):
        self.deathList = deathList
        self.helpfulToonsList = helpfulToonsList
        self.toonRewardIds = []
        for reward in rewards:
            self.toonRewardIds.append(reward[0])
        self.toonRewardDicts = toontown.battle.BattleExperience.genRewardDicts(rewards)

    def genAttackDicts(self, toons, suits, toonAttacks, suitAttacks):
        if self.track and self.track.isPlaying():
            self.notify.warning('genAttackDicts() - track is playing!')
        self.__genToonAttackDicts(toons, suits, toonAttacks)
        self.__genSuitAttackDicts(toons, suits, suitAttacks)

    def __genToonAttackDicts(self, toons, suits, toonAttacks):
        for toonAttack in toonAttacks:
            self.notify.info(toonAttack)
            targetGone = 0
            track = toonAttack[TOON_TRACK_COL]
            if track != NO_ATTACK:
                attackDict = {}
                toonIndex = toonAttack[TOON_ID_COL]
                toonId = toons[toonIndex]
                toon = self.battle.findToon(toonId)
                if not toon:
                    continue
                level = toonAttack[TOON_LVL_COL]
                attackDict['toon'] = toon
                attackDict['track'] = track
                attackDict['level'] = level
                hps = toonAttack[TOON_HP_COL]
                marketStatus=toon.getStatus(MARKETING_STATUS)
                if marketStatus:
                    marketStatusCap=marketStatus['dmgCap']
                    if marketStatusCap:
                        for hp in hps:
                            if hp > marketStatusCap:
                                hp = marketStatusCap
                kbBonuses = toonAttack[TOON_KBBONUS_COL]
                if track == NPCSOS:
                    attackDict['npcId'] = toonAttack[TOON_TGT_COL]
                    toonId = toonAttack[TOON_TGT_COL]
                    track, npc_level, npc_hp = NPCToons.getNPCTrackLevelHp(attackDict['npcId'])
                    if not track:
                        track = NPCSOS
                    attackDict['track'] = track
                    attackDict['level'] = npc_level
                elif track == PETSOS:
                    petId = toonAttack[TOON_TGT_COL]
                    attackDict['toonId'] = toonId
                    attackDict['petId'] = petId
                if track == SOS:
                    if toonAttack[TOON_TGT_COL] == base.localAvatar.doId:
                        target = base.localAvatar
                        attackDict['targetType'] = 'callee'
                    elif toon == base.localAvatar:
                        target = base.cr.identifyAvatar(toonAttack[TOON_TGT_COL])
                        attackDict['targetType'] = 'caller'
                    else:
                        target = None
                        attackDict['targetType'] = 'observer'
                    attackDict['target'] = target
                elif track in [NPCSOS, NPC_COGS_MISS, NPC_TOONS_HIT, NPC_RESTOCK_GAGS, PETSOS]:
                    attackDict['special'] = 1
                    toonHandles = []
                    for toon in toons:
                        if toon != -1:
                            target = self.battle.findToon(toon)
                            if not target:
                                continue
                            if track == NPC_TOONS_HIT and toon == toonId:
                                continue
                            toonHandles.append(target)

                    attackDict['toons'] = toonHandles
                    suitHandles = []
                    for suit in suits:
                        if suit != -1:
                            target = self.battle.findSuit(suit)
                            if not target:
                                continue
                            suitHandles.append(target)

                    attackDict['suits'] = suitHandles
                    if track == PETSOS:
                        del attackDict['special']
                        targets = []
                        for toon in toons:
                            if toon != -1:
                                target = self.battle.findToon(toon)
                                if target is None:
                                    continue
                                toonDict = {'toon': target, 'hp': hps[toons.index(toon)]}
                                self.notify.debug(
                                    'PETSOS: toon: %d healed for hp: %d' % (target.doId, hps[toons.index(toon)]))
                                targets.append(toonDict)

                        if len(targets) > 0:
                            attackDict['target'] = targets
                elif track == HEAL:
                    targets = []
                    if levelAffectsGroup(HEAL, level):
                        for toon in toons:
                            if toon != -1 and toon != toonId:
                                target = self.battle.findToon(toon)
                                if target is None:
                                    continue
                                toonDict = {'toon': target, 'hp': hps[toons.index(toon)]}
                                self.notify.debug(
                                    'HEAL: toon: %d healed for hp: %d' % (target.doId, hps[toons.index(toon)]))
                                targets.append(toonDict)
                    else:
                        targetIndex = toonAttack[TOON_TGT_COL]
                        target = self.battle.findToon(toons[targetIndex])
                        if target:
                            toonDict = {'toon': target, 'hp': hps[targetIndex]}
                            targets.append(toonDict)
                    if len(targets) > 0:
                        selfTarget = self.battle.findToon(toonId)
                        if selfTarget.getTrackPrestige(HEAL_TRACK):
                            toonDict = {'toon': selfTarget, 'hp': hps[toons.index(toonId)]}
                            self.notify.debug('HEAL: self for hp: %d' % (hps[toons.index(toonId)]))
                            targets.append(toonDict)

                        attackDict['target'] = targets
                    else:
                        targetGone = 1
                elif attackAffectsGroup(track, level, toonAttack[TOON_TRACK_COL]):
                    targets = []
                    for suit in suits:
                        if suit != -1:
                            target = self.battle.findSuit(suit)
                            if toonAttack[TOON_TRACK_COL] == NPCSOS:
                                if track == LURE and self.battle.isSuitLured(target) == 1:
                                    continue
                                elif track == TRAP and (
                                        self.battle.isSuitLured(target) == 1 or target.battleTrap != NO_TRAP):
                                    continue
                            targetIndex = suits.index(suit)
                            suitDict = {}
                            suitDict['suit'] = target
                            suitDict['hp'] = hps[targetIndex]
                            if toonAttack[TOON_TRACK_COL] == NPCSOS and track == DROP and hps[targetIndex] == 0:
                                continue
                            suitDict['hpBonus'] = toonAttack[TOON_HPBONUS_COL][targetIndex]
                            suitDict['kbBonus'] = kbBonuses[targetIndex]
                            suitDict['died'] = toonAttack[SUIT_DIED_COL] & 1 << targetIndex
                            suitDict['revived'] = toonAttack[SUIT_REVIVE_COL] & 1 << targetIndex
                            if suitDict['died'] != 0:
                                pass
                            suitDict['leftSuits'] = []
                            suitDict['rightSuits'] = []
                            targets.append(suitDict)

                    attackDict['target'] = targets
                elif track == ZAP:
                    targets = []
                    zapOrder = [-1 for _ in xrange(len(AvZapJumps[0]))]
                    for suit in suits:
                        if suit != -1:
                            target = self.battle.findSuit(suit)
                            targetIndex = suits.index(suit)
                            suitDict = {}
                            suitDict['suit'] = target
                            suitDict['hp'] = hps[targetIndex]
                            zapIndex = toonAttack[TOON_HPBONUS_COL][targetIndex]
                            if len(AvZapJumps[0]) > zapIndex >= 0:
                                zapOrder[zapIndex] = targetIndex
                            else:
                                self.notify.warning('Unexpected zap index value: %d' % zapIndex)
                            suitDict['hpBonus'] = 0
                            suitDict['kbBonus'] = 0
                            suitDict['died'] = toonAttack[SUIT_DIED_COL] & 1 << targetIndex
                            suitDict['revived'] = toonAttack[SUIT_REVIVE_COL] & 1 << targetIndex
                            if suitDict['died'] != 0:
                                pass
                            suitDict['leftSuits'] = []
                            suitDict['rightSuits'] = []
                            targets.append(suitDict)

                    attackDict['target'] = targets
                    attackDict['order'] = zapOrder
                else:
                    targetIndex = toonAttack[TOON_TGT_COL]
                    if targetIndex < 0:
                        targetGone = 1
                    else:
                        targetId = suits[targetIndex]
                        target = self.battle.findSuit(targetId)
                        suitDict = {'suit': target}
                        if self.battle.activeSuits.count(target) == 0:
                            targetGone = 1
                            suitIndex = 0
                        else:
                            suitIndex = self.battle.activeSuits.index(target)
                        leftSuits = []
                        for si in xrange(0, suitIndex):
                            asuit = self.battle.activeSuits[si]
                            if self.battle.isSuitLured(asuit) == 0:
                                leftSuits.append(asuit)

                        lenSuits = len(self.battle.activeSuits)
                        rightSuits = []
                        if lenSuits > suitIndex + 1:
                            for si in xrange(suitIndex + 1, lenSuits):
                                asuit = self.battle.activeSuits[si]
                                if self.battle.isSuitLured(asuit) == 0:
                                    rightSuits.append(asuit)

                        suitDict['leftSuits'] = leftSuits
                        suitDict['rightSuits'] = rightSuits
                        suitDict['hp'] = hps[targetIndex]
                        suitDict['hpBonus'] = toonAttack[TOON_HPBONUS_COL][targetIndex]
                        suitDict['kbBonus'] = kbBonuses[targetIndex]
                        suitDict['died'] = toonAttack[SUIT_DIED_COL] & 1 << targetIndex
                        suitDict['revived'] = toonAttack[SUIT_REVIVE_COL] & 1 << targetIndex
                        if suitDict['revived'] != 0:
                            pass
                        if suitDict['died'] != 0:
                            pass
                        attackDict['target'] = suitDict
                attackDict['sidestep'] = toonAttack[TOON_MISSED_COL]
                if 'npcId' in attackDict:
                    attackDict['sidestep'] = 0
                attackDict['battle'] = self.battle
                attackDict['playByPlayText'] = self.playByPlayText
                if targetGone == 0:
                    self.toonAttackDicts.append(attackDict)
                else:
                    self.notify.warning('genToonAttackDicts() - target gone!')

        def compFunc(a, b):
            alevel = a['level']
            blevel = b['level']
            if alevel > blevel:
                return 1
            elif alevel < blevel:
                return -1
            return 0

        self.toonAttackDicts.sort(compFunc)
        return

    def __findToonAttack(self, track):
        setCapture = 0
        matchedAttacks = []
        for toonAttack in self.toonAttackDicts:
            if toonAttack['track'] == track or track == NPCSOS and 'special' in toonAttack:
                matchedAttacks.append(toonAttack)

        if track == TRAP:
            sortedTraps = []
            for attack in matchedAttacks:
                if 'npcId' not in attack:
                    sortedTraps.append(attack)

            for attack in matchedAttacks:
                if 'npcId' in attack:
                    sortedTraps.append(attack)

            matchedAttacks = sortedTraps
        if setCapture:
            pass
        return matchedAttacks

    def __genStatusUpdates(self):
        pass

    @staticmethod
    def __getSuitAtkFromString(atkString, toons):
        # Format: int8, int8, int8, int16[], int8, int8, int8
        dg = PyDatagram(atkString)
        dgi = PyDatagramIterator(dg)
        suitId = dgi.getInt8()
        suitAtk = dgi.getInt8()
        suitTarget = dgi.getInt8()
        suitDamages = []
        for i in xrange(len(toons)):
            suitDamages.append(dgi.getInt16())
        suitDefeats = dgi.getInt8()
        suitBeforeToons = dgi.getInt8()
        suitTaunt = dgi.getInt8()
        return suitId, suitAtk, suitTarget, suitDamages, suitDefeats, suitBeforeToons, suitTaunt

    def __genSuitAttackDicts(self, toons, suits, suitAttacks):
        for suitAttack in suitAttacks:
            targetGone = 0
            attack = suitAttack[SUIT_ATK_COL]
            if attack != NO_ATTACK:
                suitIndex = suitAttack[SUIT_ID_COL]
                suitId = suits[suitIndex]
                suit = self.battle.findSuit(suitId)
                if not suit:
                    self.notify.error('suit: %d not in battle!' % suitId)
                attackDict = getSuitAttack(suit.getStyleName(), suit.getLevel(), attack)
                attackDict['suit'] = suit
                attackDict['battle'] = self.battle
                attackDict['playByPlayText'] = self.playByPlayText
                attackDict['taunt'] = suitAttack[SUIT_TAUNT_COL]
                hps = suitAttack[SUIT_HP_COL]
                if attackDict['group'] == ATK_TGT_GROUP:
                    targets = []
                    for t in toons:
                        if t != -1:
                            target = self.battle.findToon(t)
                            if not target:
                                continue
                            targetIndex = toons.index(t)
                            tdict = {}
                            tdict['toon'] = target
                            tdict['hp'] = hps[targetIndex]
                            self.notify.debug('DAMAGE: toon: %d hit for hp: %d' % (target.doId, hps[targetIndex]))
                            tdict['died'] = suitAttack[TOON_DIED_COL] & 1 << targetIndex
                            targets.append(tdict)

                    if len(targets) > 0:
                        attackDict['target'] = targets
                    else:
                        targetGone = 1
                elif attackDict['group'] == ATK_TGT_SINGLE:
                    targetIndex = suitAttack[SUIT_TGT_COL]
                    targetId = toons[targetIndex]
                    target = self.battle.findToon(targetId)
                    if not target:
                        targetGone = 1
                    else:
                        self.notify.debug('DAMAGE: toon: %d hit for hp: %d' % (target.doId, hps[targetIndex]))
                        tdict = {'toon': target,
                                 'hp': hps[targetIndex],
                                 'died': suitAttack[TOON_DIED_COL] & 1 << targetIndex}
                        toonIndex = self.battle.activeToons.index(target)
                        rightToons = []
                        for ti in xrange(0, toonIndex):
                            rightToons.append(self.battle.activeToons[ti])
                        lenToons = len(self.battle.activeToons)
                        leftToons = []
                        if lenToons > toonIndex + 1:
                            for ti in xrange(toonIndex + 1, lenToons):
                                leftToons.append(self.battle.activeToons[ti])
                        tdict['leftToons'] = leftToons
                        tdict['rightToons'] = rightToons
                        attackDict['target'] = tdict
                else:
                    self.notify.warning('got suit attack not group or single!')
                if targetGone == 0:
                    self.suitAttackDicts.append(attackDict)
                else:
                    self.notify.warning('genSuitAttackDicts() - target gone!')

        return

    # This is just copy-pasted, actually fill this out later.
    def __genSuitCheatDicts(self, toons, suits, suitCheats):
        for suitCheat in suitCheats:
            targetGone = 0
            attack = suitCheat[SUIT_ATK_COL]
            if attack == HEAL_CHEAT:
                suitIndex = suitCheat[SUIT_ID_COL]
                suitId = suits[suitIndex]
                suit = self.battle.findSuit(suitId)
                if not suit:
                    self.notify.error('suit: %d not in battle!' % suitId)

                cheatDict = {}
                cheatDict['suit'] = suit
                cheatDict['battle'] = self.battle
                cheatDict['playByPlayText'] = self.playByPlayText
                cheatDict['taunt'] = suitCheat[SUIT_TAUNT_COL]
                hps = suitCheat[SUIT_HP_COL]
                if cheatDict['group'] == ATK_TGT_GROUP:
                    targets = []
                    for t in toons:
                        if t != -1:
                            target = self.battle.findToon(t)
                            if not target:
                                continue
                            targetIndex = toons.index(t)
                            tdict = {}
                            tdict['toon'] = target
                            tdict['hp'] = hps[targetIndex]
                            self.notify.debug('DAMAGE: toon: %d hit for hp: %d' % (target.doId, hps[targetIndex]))
                            tdict['died'] = suitCheat[TOON_DIED_COL] & 1 << targetIndex
                            targets.append(tdict)

                    if len(targets) > 0:
                        cheatDict['target'] = targets
                    else:
                        targetGone = 1
                elif cheatDict['group'] == ATK_TGT_SINGLE:
                    targetIndex = suitCheat[SUIT_TGT_COL]
                    targetId = toons[targetIndex]
                    target = self.battle.findToon(targetId)
                    if not target:
                        targetGone = 1
                    else:
                        self.notify.debug('DAMAGE: toon: %d hit for hp: %d' % (target.doId, hps[targetIndex]))
                        tdict = {'toon': target,
                                 'hp': hps[targetIndex],
                                 'died': suitCheat[TOON_DIED_COL] & 1 << targetIndex}
                        toonIndex = self.battle.activeToons.index(target)
                        rightToons = []
                        for ti in xrange(0, toonIndex):
                            rightToons.append(self.battle.activeToons[ti])
                        lenToons = len(self.battle.activeToons)
                        leftToons = []
                        if lenToons > toonIndex + 1:
                            for ti in xrange(toonIndex + 1, lenToons):
                                leftToons.append(self.battle.activeToons[ti])
                        tdict['leftToons'] = leftToons
                        tdict['rightToons'] = rightToons
                        cheatDict['target'] = tdict
                else:
                    self.notify.warning('got suit attack not group or single!')
                if targetGone == 0:
                    self.suitCheatDicts.append(cheatDict)
                else:
                    self.notify.warning('genSuitCheatDicts() - target gone!')
            elif attack == ATTACK_CHEAT:
                suitIndex = suitCheat[SUIT_ID_COL]
                suitId = suits[suitIndex]
                suit = self.battle.findSuit(suitId)
                if not suit:
                    self.notify.error('suit: %d not in battle!' % suitId)

                cheatDict = getSuitAttack(suit.getStyleName(), suit.getLevel(), attack)
                cheatDict['suit'] = suit
                cheatDict['battle'] = self.battle
                cheatDict['playByPlayText'] = self.playByPlayText
                cheatDict['taunt'] = suitCheat[SUIT_TAUNT_COL]
                hps = suitCheat[SUIT_HP_COL]
                if cheatDict['group'] == ATK_TGT_GROUP:
                    targets = []
                    for t in toons:
                        if t != -1:
                            target = self.battle.findToon(t)
                            if not target:
                                continue
                            targetIndex = toons.index(t)
                            tdict = {}
                            tdict['toon'] = target
                            tdict['hp'] = hps[targetIndex]
                            self.notify.debug('DAMAGE: toon: %d hit for hp: %d' % (target.doId, hps[targetIndex]))
                            tdict['died'] = suitCheat[TOON_DIED_COL] & 1 << targetIndex
                            targets.append(tdict)

                    if len(targets) > 0:
                        cheatDict['target'] = targets
                    else:
                        targetGone = 1
                elif cheatDict['group'] == ATK_TGT_SINGLE:
                    targetIndex = suitCheat[SUIT_TGT_COL]
                    targetId = toons[targetIndex]
                    target = self.battle.findToon(targetId)
                    if not target:
                        targetGone = 1
                    else:
                        self.notify.debug('DAMAGE: toon: %d hit for hp: %d' % (target.doId, hps[targetIndex]))
                        tdict = {'toon': target,
                                 'hp': hps[targetIndex],
                                 'died': suitCheat[TOON_DIED_COL] & 1 << targetIndex}
                        toonIndex = self.battle.activeToons.index(target)
                        rightToons = []
                        for ti in xrange(0, toonIndex):
                            rightToons.append(self.battle.activeToons[ti])
                        lenToons = len(self.battle.activeToons)
                        leftToons = []
                        if lenToons > toonIndex + 1:
                            for ti in xrange(toonIndex + 1, lenToons):
                                leftToons.append(self.battle.activeToons[ti])
                        tdict['leftToons'] = leftToons
                        tdict['rightToons'] = rightToons
                        cheatDict['target'] = tdict
                else:
                    self.notify.warning('got suit attack not group or single!')
                if targetGone == 0:
                    self.suitCheatDicts.append(cheatDict)
                else:
                    self.notify.warning('genSuitCheatDicts() - target gone!')

        return

    def __doSuitAttacks(self):
        if base.config.GetBool('want-suit-anims', 1):
            track = Sequence(name='suit-attacks')
            camTrack = Sequence(name='suit-attacks-cam')
            isLocalToonSad = False
            for update in self.suitPreStatusUpdates:
                break
            for attack in self.suitAttackDicts:
                battle = attack['battle']
                suit = attack['suit']
                if battle.isSuitLured(suit):
                    resetTrack = MovieSuitAttacks.getResetTrack(suit, battle)
                    track.append(resetTrack)
                    waitTrack = Sequence(Wait(resetTrack.getDuration()), Func(battle.unlureSuit, suit))
                    camTrack.append(waitTrack)
                interval, cameraInterval = MovieSuitAttacks.doSuitAttack(attack)
                if interval:
                    track.append(interval)
                    camTrack.append(cameraInterval)
                targetField = attack.get('target')
                if targetField is None:
                    continue
                if attack['group'] == ATK_TGT_GROUP:
                    for target in targetField:
                        if target['died'] and target['toon'].doId == base.localAvatar.doId:
                            isLocalToonSad = True

                elif attack['group'] == ATK_TGT_SINGLE:
                    if targetField['died'] and targetField['toon'].doId == base.localAvatar.doId:
                        isLocalToonSad = True
                if isLocalToonSad:
                    break
            for update in self.suitPostStatusUpdates:
                break

            if len(track) == 0:
                return None, None
            return track, camTrack
        else:
            return None, None

    def __doSuitCheats(self):
        if base.config.GetBool('want-suit-anims', 1):
            track = Sequence(name='suit-attacks')
            camTrack = Sequence(name='suit-attacks-cam')
            isLocalToonSad = False
            for update in self.suitPreStatusUpdates:
                break
            for cheat in self.suitCheatDicts:
                battle = cheat['battle']
                suit = cheat['suit']
                if battle.isSuitLured(suit):
                    resetTrack = MovieSuitAttacks.getResetTrack(suit, battle)
                    track.append(resetTrack)
                    waitTrack = Sequence(Wait(resetTrack.getDuration()), Func(battle.unlureSuit, suit))
                    camTrack.append(waitTrack)
                interval, cameraInterval = MovieSuitCheats.doSuitCheat(cheat)
                if interval:
                    track.append(interval)
                    camTrack.append(cameraInterval)
                targetField = cheat.get('target')
                if targetField is None:
                    continue
                if cheat['group'] == ATK_TGT_GROUP:
                    for target in targetField:
                        if target['died'] and target['toon'].doId == base.localAvatar.doId:
                            isLocalToonSad = True

                elif cheat['group'] == ATK_TGT_SINGLE:
                    if targetField['died'] and targetField['toon'].doId == base.localAvatar.doId:
                        isLocalToonSad = True
                if isLocalToonSad:
                    break
            for update in self.suitPostStatusUpdates:
                break

            if len(track) == 0:
                return None, None
            return track, camTrack
        else:
            return None, None
