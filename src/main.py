from lib.dbabstraction import DataManager
from lib.telegram_binding import TelegramBot

import logging
import yaml
import sys

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

class App():
    def __init__(self):
        self.config = False

        with open("config.yaml", 'r') as f:
            self.config = yaml.load(f, yaml.SafeLoader)

        if not self.config:
            logging.FATAL("Failed to load configuration file!")
            sys.exit(1)

        self.dm = DataManager(self.config['sqlite_path'])
        self.tb = TelegramBot(self.config['bot_token'], self.dm)

    def start(self):
        self.tb.start()

if __name__ == '__main__':
    app = App()
    app.start()

