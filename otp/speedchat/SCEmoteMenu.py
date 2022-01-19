from SCMenu import SCMenu
from SCEmoteTerminal import SCEmoteTerminal
from otp.avatar import Emote
from otp.otpbase import OTPLocalizer


class SCEmoteMenu(SCMenu):

    def __init__(self):
        SCMenu.__init__(self)
        self.accept('emotesChanged', self.__emoteAccessChanged)
        self.__emoteAccessChanged()

    def destroy(self):
        SCMenu.destroy(self)

    def __emoteAccessChanged(self):
        self.clearMenu()
        try:
            lt = base.localAvatar
        except:
            return

        for i in xrange(len(lt.emoteAccess)):
            if lt.emoteAccess[i]:
                self.append(SCEmoteTerminal(i))
