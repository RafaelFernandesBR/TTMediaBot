import re
import time
import traceback


from bot.streamer import Streamer
from .commands import *


class CommandProcessor(object):
    def __init__(self, player, ttclient, service_manager):
        self.player = player
        self.ttclient = ttclient
        self.service_manager = service_manager
        self.streamer = Streamer(self.service_manager)
        self.commands_dict = {
            'h': self.help,
            'a': AboutCommand(self),
            'p': PlayPauseCommand(self),
            'u': PlayUrlCommand(self),
            'sv': ServiceCommand(self),
            's': StopCommand(self),
            'n': NextTrackCommand(self),
            'c': SelectTrackCommand(self),
            'b': PreviousTrackCommand(self),
            'sf': SeekForwardCommand(self),
            'ps': PositionCommand(self),
            'sb': SeekBackCommand(self),
            'v': VolumeCommand(self),
            'r': RateCommand(self),
            'm': ModeCommand(self),
            'dl': lambda arg, user: self.player.track.url,
        }
        self.admin_commands_dict = {
            'girl': lambda arg, user: 'Настенька',
            'cn': ChangeNicknameCommand(self),
        }


    def __call__(self, message, user):
        if user.is_banned:
            return _('You are banned')
        if not user.is_admin:
            if user.channel_id != self.ttclient.get_my_channel_id():
                return _('You aren\'t in channel with bot')
        try:    
            command = re.findall('[a-z]+', message.split(' ')[0].lower())[0]
        except IndexError:
            return self.help()
        arg = ' '.join(message.split(' ')[1::])
        try:
            if command in self.commands_dict:
                return self.commands_dict[command](arg, user)
            elif user.is_admin and command in self.admin_commands_dict:
                return self.admin_commands_dict[command](arg, user)
            else:
                return _('Unknown command.\n') + self.help()
        except Exception as e:
            traceback.print_exc()
            return f'error: {e}'

    def help(self, arg=None, user=None):
        help_strings = []
        for i in list(self.commands_dict)[1::]:
            try:
                help_strings.append(
                    '{}: {}'.format(i, self.commands_dict[i].help)
                )
            except AttributeError:
                help_strings.append('{}: help text not found'.format(i))
        if user and user.is_admin:
            for i in list(self.admin_commands_dict)[1::]:
                try:
                    help_strings.append(
                        '{}: {}'.format(i, self.admin_commands_dict[i].help)
                    )
                except AttributeError:
                    help_strings.append('{}: help text not found'.format(i))
        return '\n'.join(help_strings)
