import logging
import queue
import sys
import time

from pydantic.error_wrappers import ValidationError

from bot import cache, commands, config, connectors, logger, modules, player, services, sound_devices, TeamTalk, translator, vars


class Bot:
    def __init__(self, config_file_name, cache_file_name, log_file_name):
        try:
            self.config = config.Config(config_file_name)
        except ValidationError as e:
            for error in e.errors():
                print("Error in config:", ".".join(error["loc"]), error["msg"])
            sys.exit(1)
        except PermissionError:
            sys.exit('The configuration file cannot be accessed due to a permission error or is already used by another instance of the bot')
        translator.install_locale(self.config.general.language)
        try:
            if cache_file_name:
                self.cache = cache.Cache(cache_file_name)
            else:
                self.cache = cache.Cache(self.config.general.cache_file_name)
        except PermissionError:
            sys.exit('The cache file cannot be accessed due to a permission error or is already used by another instance of the bot')
        self.log_file_name = log_file_name
        self.player = player.Player(self.config.player, self.cache)
        self.ttclient = TeamTalk.TeamTalk(self)
        self.tt_player_connector = connectors.TTPlayerConnector(self.player, self.ttclient)
        self.sound_device_manager = sound_devices.SoundDeviceManager(self.config.sound_devices, self. player, self.ttclient)
        self.service_manager = services.ServiceManager(self.config.services)
        self.module_manager = modules.ModuleManager(self.config, self.player, self.ttclient, self.service_manager)
        self.command_processor = commands.CommandProcessor(self, self.config, self.player, self.ttclient, self.module_manager, self.service_manager, self.cache)

    def initialize(self):
        if self.config.logger.log:
            logger.initialize_logger(self.config.logger, self.log_file_name)
        logging.debug('Initializing')
        self.sound_device_manager.initialize()
        self.ttclient.initialize()
        self.player.initialize()
        self.service_manager.initialize()
        logging.debug('Initialized')

    def run(self):
        logging.debug('Starting')
        self.ttclient.run()
        self.player.run()
        self.tt_player_connector.start()
        self.command_processor.run()
        logging.info('Started')
        self._close = False
        while not self._close:
            try:
                message = self.ttclient.message_queue.get_nowait()
                logging.info("New message {text} from {username}".format(text=message.text, username=message.user.username))
                self.command_processor(message)
            except queue.Empty:
                pass
            time.sleep(vars.loop_timeout)


    def close(self):
        logging.debug('Closing bot')
        self.player.close()
        self.ttclient.close()
        self.tt_player_connector.close()
        self.config.close()
        self.cache.close()
        self._close = True
        logging.info('Bot closed')
