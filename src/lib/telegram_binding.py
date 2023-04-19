import logging

from enum import Enum

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler

from dataclasses import dataclass

from datetime import datetime

from lib.util import ConsumptionEntry
from lib.dbabstraction import DBConsumptionEntry

class BotStates(Enum):
    IDLE = 0
    NEW_ENTRY = 1


@dataclass
class BotResponses():

    start_or_help = "You are completing another task, use the /reset command to loose all progress and reset back to idle state."

    bot_not_idle = "You are completing another task, use the /reset command to loose all progress and reset back to idle state."
    unknown_command = "I didn't understand that, im sorry."

    response_already_idle = "The bot is already in idle (default) state :-)"
    returned_to_idle = "You have returned to the idle state.\nAll progress from potential previous operations has been discarded."

    create_new_entry = "For creating a new fuel consumption tracking entry, i require additional information in the following format:\n\nodo:\t<current milage on the odometer>\ndist:\t<distance travelled for the entry>\nliters:\t<how much fuel did it take to fill up>\nbill:\t<how much did it cost to fill up>"
    new_entry_complete = "Entry has been added."
    new_entry_incomplete = "I am still missing some information."

    error_new_entry_invalid_input = "I was unable to make sense of your gibberish."
    error_opdata_state_mismatch = "Operational data does not match current context. Contact the Developer."


class NewFCEntry():
    def __init__(self):
        self.odo:    int   = False
        self.dist:   float = False
        self.liters: float = False
        self.bill:   float = False

    def complete(self):
        if not self.odo == False and not self.dist == False and not self.liters == False and not self.bill == False:
            return True
        else:
            return False

class TelegramBot():
    def __init__(self, bot_token, dm):
        self.__token = bot_token
        self.dm = dm
        self.bot_state = BotStates.IDLE
        self.operational_data = False

        self.application = ApplicationBuilder().token(self.__token).build()

        self.__add_handlers()

    def __add_handlers(self):
        self.application.add_handler(CommandHandler('new', self.bot_new))
        self.application.add_handler(CommandHandler('start', self.bot_start))
        self.application.add_handler(CommandHandler('reset', self.bot_reset))
        self.application.add_handler(CommandHandler('hist', self.bot_hist))
        self.application.add_handler(CommandHandler('list', self.bot_list))

        self.application.add_handler(MessageHandler(filters.TEXT, self.bot_generic_message))

        self.application.add_handler(MessageHandler(filters.COMMAND, self.bot_unknown_command))

    def start(self):
        self.application.run_polling()

    # actual bot funcationality
    async def bot_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state != BotStates.IDLE:
            await self.__generic_response(update, context, BotResponses.bot_not_idle)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.create_new_entry)
        self.bot_state = BotStates.NEW_ENTRY
        self.operational_data = NewFCEntry()

    async def bot_hist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(update.message.text)

    async def bot_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command = update.message.text.split(' ')
        count = 5
        if len(command) > 1:
            count = int(command[1])
        
        data = self.dm.list_entries(count)
        for d in data:
            human_readable_timestamp = datetime.strftime(datetime.fromtimestamp(d.entry_ts), '%d\.%m\.%Y %H:%M')
            message_text = f"""
            *{human_readable_timestamp}* @ `{d.odometer} km`
            Consumption `{d.consumption:.2f}L` / `{d.consumption_price:.2f}€` per 100km
            Price `{d.price_per_liter:.2f}€` per Liter"""
            await self.__generic_response(update, context, message_text, parse_mode=ParseMode.MARKDOWN_V2)

    # basic bot commands (start, reset, message handling)
    async def bot_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state != BotStates.IDLE:
            await self.__generic_response(update, context, BotResponses.bot_not_idle)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.start_or_help)

    async def bot_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state == BotStates.IDLE:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.response_already_idle)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.returned_to_idle)
            self.bot_state = BotStates.IDLE

    async def bot_generic_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state == BotStates.NEW_ENTRY:
            await self.__bot_new_entry_message_parsing(update, context)
        else:
            await self.bot_unknown_command(update, context)

    async def bot_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.unknown_command)

    async def __generic_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text, parse_mode=None):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=parse_mode)

    # message parsing
    async def __bot_new_entry_message_parsing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if type(self.operational_data) != NewFCEntry:
            await self.__generic_response(update, context, BotResponses.error_opdata_state_mismatch)
            return
        for l in update.message.text.split('\n'):
            data = l.split(':')

            if len(data) != 2:
                await self.__generic_response(update, context, BotResponses.error_new_entry_invalid_input)
                return

            key   = str(data[0]).strip()
            value = str(data[1]).strip()

            match key:
                case 'odo':
                    self.operational_data.odo = int(value)
                case 'dist':
                    self.operational_data.dist = float(value)
                case 'liters':
                    self.operational_data.liters = float(value)
                case 'bill':
                    self.operational_data.bill = float(value)
                case _:
                    await self.__generic_response(update, context, BotResponses.error_new_entry_invalid_input)
                    return
                
        if self.operational_data.complete():
            self.dm.add_entry(ConsumptionEntry(
                self.operational_data.odo,
                self.operational_data.dist, 
                self.operational_data.liters, 
                self.operational_data.bill
            ))
            self.operational_data = False
            self.bot_state = BotStates.IDLE
            await self.__generic_response(update, context, BotResponses.new_entry_complete)
        else:
            await self.__generic_response(update, context, BotResponses.new_entry_incomplete)
