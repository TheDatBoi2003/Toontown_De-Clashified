import os
import shutil
import datetime
from panda3d.core import *
from direct.directnotify import DirectNotifyGlobal
from direct.distributed import DistributedObject
from direct.showbase import AppRunnerGlobal
from toontown.toonbase import TTLocalizer

class StreetSign(DistributedObject.DistributedObject):
    StreetSignFileName = config.GetString('street-sign-filename', 'texture.jpg')
    StreetSignBaseDir = config.GetString('street-sign-base-dir', 'sign')
    notify = DirectNotifyGlobal.directNotify.newCategory('StreetSign')

    def __init__(self):
        self.redownloadStreetSign()

    def replaceTexture(self):
        pass

    def redownloadStreetSign(self):
        pass

    def downloadStreetSignTask(self, task):
        pass
