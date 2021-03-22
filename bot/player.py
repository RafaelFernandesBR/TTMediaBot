from enum import Enum
import vlc
from threading import Thread
import time
import random

from . import errors
from .track import Track

class Player:
    def __init__(self, ttclient, config):
        self._ttclient = ttclient
        self.config = config
        self._vlc_instance = vlc.Instance()
        self._vlc_player = self._vlc_instance.media_player_new()
        if self.config:
            self._vlc_player.audio_set_volume(self.config['default_volume'])
            self.max_volume = self.config['max_volume']
            self.faded_volume = self.config['faded_volume']
            self.faded_volume_timestamp = self.config['faded_volume_timestamp']
            self.seek_step = config['seek_step']
            self.output_device = self.config['output_device']
            self.input_device = self.config['input_device']
        else:
            self.output_device = 0
            self.input_device = 0
        self.output_devices = self.get_output_devices()
        self.input_devices = self.get_input_devices()
        self.initialize_devices()
        self.track_list = []
        self.track = Track()
        self.track_index = -1
        self.state = State.Stopped
        self.mode = Mode.Single
        self.playing_thread = PlayingThread(self)
        if self.config:
            self.playing_thread.start()

    def play(self, tracks=None):
        if tracks:
            self.track_list = tracks
            if self.mode == Mode.Random:
                self.track = random.choice(self.track_list)
                self.track_index = self.track_list.index(self.track)
            else:
                self.track_index = 0
                self.track = tracks[self.track_index]
            self._play_with_vlc(self.track.url)
        else:
            self._vlc_player.play()
        while self._vlc_player.get_state() != vlc.State.Playing and self._vlc_player.get_state() != vlc.State.Ended:
            pass    
        self.state = State.Playing


    def pause(self):
        self.state = State.Paused
        self._vlc_player.pause()

    def stop(self):
        self.state = State.Stopped
        self._vlc_player.pause()
        self.track_index = -1
        self.track = Track()
        self.track_list = []


    def _play_with_vlc(self, arg):
        self._vlc_player.set_media(self._vlc_instance.media_new(arg))
        self._vlc_player.play()

    def next(self):
        track_index = self.track_index
        if self.mode == Mode.Random:
            track_index = random.randint(0, len(self.track_list))
        else:
            track_index += 1
        try:
            self.play_by_index(track_index)
        except errors.IncorrectTrackIndexError:
            raise errors.NoNextTrackError()

    def previous(self):
        track_index = self.track_index
        if self.mode == Mode.Random:
            track_index = random.randint(0, len(self.track_list))
        else:
            track_index -= 1
        try:
            self.play_by_index(track_index)
        except errors.IncorrectTrackIndexError:
            raise errors.NoPreviousTrackError

    def play_by_index(self, index):
        if self.state == State.Stopped:
            raise errors.NothingIsPlayingError()
        if index >= 0 and index < len(self.track_list):
            self.track_index = index
            self.track = self.track_list[self.track_index]
            self._play_with_vlc(self.track.url)
            if self.state == State.Paused:
                while self._vlc_player.get_state() != vlc.State.Playing and self._vlc_player.get_state() != vlc.State.Ended:
                    pass    
                self.state = State.Playing
        else:
            raise errors.IncorrectTrackIndexError()

    def get_volume(self):
        return self._vlc_player.audio_get_volume()


    def set_volume(self, volume):
        volume = volume if volume <= self.max_volume else self.max_volume
        if self.faded_volume:
            n = 1 if self._vlc_player.audio_get_volume() < volume else -1
            for i in range(self._vlc_player.audio_get_volume(), volume, n):
                self._vlc_player.audio_set_volume(i)
                time.sleep(self.faded_volume_timestamp)
        else:
            self._vlc_player.audio_set_volume(volume)

    def get_rate(self):
        return self._vlc_player.get_rate()

    def set_rate(self, arg):
        self._vlc_player.set_rate(arg)

    def seek_back(self, time_step=None):
        time_step = time_step / 100 if time_step else self.seek_step / 100
        pos = self._vlc_player.get_position() - time_step
        if pos < 0:
            pos = 0
        elif pos > 1:
            pos = 1
        self._vlc_player.set_position(pos)

    def seek_forward(self, time_step=None):
        time_step = time_step / 100 if time_step else self.seek_step / 100
        pos = self._vlc_player.get_position() + time_step
        if pos < 0:
            pos = 0
        elif pos > 1:
            pos = 1
        self._vlc_player.set_position(pos)

    def get_position(self):
        if self.state != State.Stopped:
            return self._vlc_player.get_position() * 100
        else:
            raise errors.NothingIsPlayingError()

    def set_position(self, arg):
        if arg >= 0 and arg <= 100:
            self._vlc_player.set_position(arg)
        else:
            raise errors.IncorrectPositionError()

    def get_output_devices(self):
        devices = {}
        mods = self._vlc_player.audio_output_device_enum()
        if mods:
            mod = mods
            while mod:
                mod = mod.contents
                devices[str(mod.description, 'utf-8')] = mod.device
                mod = mod.next
        vlc.libvlc_audio_output_device_list_release(mods)
        return devices

    def get_input_devices(self):
        devices = {}
        device_list = [i for i in self._ttclient.getSoundDevices()]
        for device in device_list:
            devices[device.szDeviceName] = device.nDeviceID
        return devices

    def initialize_devices(self):
        self._vlc_player.audio_output_device_set(None, self.output_devices[list(self.output_devices)[self.output_device]])
        self._ttclient.initSoundInputDevice(self.input_devices[list(self.input_devices)[self.input_device]])

class State(Enum):
    Stopped = 'Stopped'
    Playing = 'Playing'
    Paused = 'Paused'

class Mode(Enum):
    Single = 0
    TrackList = 1
    Random = 2



class PlayingThread(Thread):
    def __init__(self, player):
        Thread.__init__(self)
        self.player = player

    def run(self):
        while True:
            if self.player.state == State.Playing and self.player._vlc_player.get_state() == vlc.State.Ended:
                if self.player.mode == Mode.Single:
                    self.player.stop()
                elif self.player.mode == Mode.TrackList or self.player.mode == Mode.Random:
                    try:
                        self.player.next()
                    except errors.NoNextTrackError:
                        self.player.stop()
            if self.player.state == State.Playing and self.player.track.from_url:
                media = self.player._vlc_player.get_media()
                media.parse_with_options(vlc.MediaParseFlag.do_interact, 0)
                new_name = media.get_meta(12)
                if not new_name:
                    new_name = "{} - {}".format(media.get_meta(vlc.Meta.Title), media.get_meta(vlc.Meta.Artist))
                if self.player.track.name != new_name:
                    self.player.track.name = new_name
            time.sleep(0.01)
