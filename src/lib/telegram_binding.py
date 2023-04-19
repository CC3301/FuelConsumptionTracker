import logging

from enum import Enum

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler

from dataclasses import dataclass

from datetime import datetime

from lib.util import ConsumptionEntry, Car
from lib.graphingtools import GraphingHelper

class BotStates(Enum):
    IDLE = 0
    NEW_ENTRY = 1
    NEW_CAR = 2


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

    create_new_car = "For creating a new Car, i need a name that you can identify:\n\nname <car name>"
    new_car_complete = "Added new Car"

    error_new_entry_invalid_input = "I was unable to make sense of your gibberish."
    error_opdata_state_mismatch = "Operational data does not match current context. Contact the Developer."
    error_no_car_selected = "No car has been selected to add the Entry to.\nYou can do so using the /car command."


class NewFCEntry():
    def __init__(self):
        self.odo:    int   = False
        self.dist:   float = False
        self.liters: float = False
        self.bill:   float = False
        self.car_id: int   = False

    def complete(self):
        if not self.odo == False and not self.dist == False and not self.liters == False and not self.bill == False and not self.car_id == False:
            return True
        return False

class NewCar():
    def __init__(self):
        self.name: str = False

    def complete(self):
        if not self.name == False:
            return True
        return False

class TelegramBot():
    def __init__(self, bot_token, dm, tmpdir):
        self.__token = bot_token
        self.dm = dm
        self.graphing = GraphingHelper(self.dm, tmpdir)
        self.bot_state = BotStates.IDLE
        self.operational_data = False
        self.botcontext = {
            'selected_car_id': False
        }

        self.application = ApplicationBuilder().token(self.__token).build()

        self.__add_handlers()

    def __add_handlers(self):
        self.application.add_handler(CommandHandler('new', self.bot_new_fc_entry))
        self.application.add_handler(CommandHandler('start', self.bot_start))
        self.application.add_handler(CommandHandler('reset', self.bot_reset))
        self.application.add_handler(CommandHandler('hist', self.bot_hist))
        self.application.add_handler(CommandHandler('list', self.bot_list))
        self.application.add_handler(CommandHandler('car', self.bot_car))
        self.application.add_handler(CommandHandler('newcar', self.bot_new_car))

        self.application.add_handler(MessageHandler(filters.TEXT, self.bot_generic_message))

        self.application.add_handler(MessageHandler(filters.COMMAND, self.bot_unknown_command))

    def start(self):
        self.application.run_polling()

    # actual bot funcationality
    async def bot_new_fc_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state != BotStates.IDLE:
            await self.__generic_response(update, context, BotResponses.bot_not_idle)
        elif self.botcontext['selected_car_id'] == False:
            await self.__generic_response(update, context, BotResponses.error_no_car_selected)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.create_new_entry)
            self.bot_state = BotStates.NEW_ENTRY
            self.operational_data = NewFCEntry()

    async def bot_new_car(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state != BotStates.IDLE:
            await self.__generic_response(update, context, BotResponses.bot_not_idle)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.create_new_car)
            self.bot_state = BotStates.NEW_CAR
            self.operational_data = NewCar()

    # provide historical data
    async def bot_hist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command = update.message.text.split(' ')
        mode = "con"
        timeframe = datetime.now().timestamp() - 100000

        if len(command) == 3:
            mode = str(command[1])
            timeframe = int(command[2])

        match mode:
            case "con":
                await self.__historical_data_consumption(update, context, timeframe)
            case "price":
                await self.__historical_data_price(update, context, timeframe)
            case _:
                await self.bot_unknown_command(update, context)
    
    async def __historical_data_consumption(self, update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
        if self.botcontext['selected_car_id'] == False:
            await self.__generic_response(update, context, BotResponses.error_no_car_selected)
        else:
            data = self.graphing.create_historical_consumption_graph(timeframe, self.botcontext['selected_car_id'])
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=data)

    async def __historical_data_price(self, update, context, timeframe):
        if self.botcontext['selected_car_id'] == False:
            await self.__generic_response(update, context, BotResponses.error_no_car_selected)
        else:
            data = self.graphing.create_historical_price_per_liter_graph(timeframe, self.botcontext['selected_car_id'])

    async def bot_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command = update.message.text.split(' ')
        count = 5
        if len(command) > 1:
            count = int(command[1])
        
        data = self.dm.list_fc_entries(count)
        for d in data:
            human_readable_timestamp = datetime.strftime(datetime.fromtimestamp(d.entry_ts), '%d\.%m\.%Y %H:%M')
            car = self.dm.get_car(d.car_id)
            for c in car:
                car = c
            message_text = f"""
            *{human_readable_timestamp}* for *{car.name}* @ `{d.odometer} km`
            Consumption `{d.consumption:.2f}L` / `{d.consumption_price:.2f}€` per 100km
            Price `{d.price_per_liter:.2f}€` per Liter"""
            await self.__generic_response(update, context, message_text, parse_mode=ParseMode.MARKDOWN_V2)

    async def bot_car(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command = update.message.text.split(' ')
        data = self.dm.list_cars()
        found_car = False
        for d in data:
            if len(command) > 1:
                if d.id == int(command[1]):
                    found_car = d
            else:
                message_text = f"""
                The following Cars are available:\n
                \- {d.name} \(ID: `{d.id}`\)"""
        if found_car != False:
            self.botcontext['selected_car_id'] = found_car.id
            message_text = f"""
            Selected {found_car.name}
            """
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

    # determine how to parse message
    async def bot_generic_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_state == BotStates.NEW_ENTRY:
            await self.__bot_new_entry_message_parsing(update, context)
        elif self.bot_state == BotStates.NEW_CAR:
            await self.__bot_new_car_message_parsing(update, context)
        else:
            await self.bot_unknown_command(update, context)

    async def bot_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=BotResponses.unknown_command)

    async def __generic_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text, parse_mode=None):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=parse_mode)

    # message parsing
    async def __bot_new_car_message_parsing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if type(self.operational_data) != NewCar:
            await self.__generic_response(update, context, BotResponses.error_opdata_state_mismatch)
            return
        for l in update.message.text.split('\n'):
            data = l .split(':')

            if len(data) != 2:
                await self.__generic_response(update, context, BotResponses.error_new_entry_invalid_input)
                return

            key   = str(data[0]).strip()
            value = str(data[1]).strip()

            match key:
                case 'name':
                    self.operational_data.name = str(value)
                case _:
                    await self.__generic_response(update, context, BotResponses.error_new_entry_invalid_input)
                    return
                
            if self.operational_data.complete():
                self.dm.add_new_car(
                    Car(
                        self.operational_data.name
                    )
                )
                self.operational_data = False
                self.bot_state = BotStates.IDLE
                await self.__generic_response(update, context, BotResponses.new_car_complete)
            else:
                await self.__generic_response(update, context, BotResponses.new_entry_incomplete)


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
        self.operational_data.car_id = self.botcontext['selected_car_id']
        if self.operational_data.complete():
            self.dm.add_fc_entry(ConsumptionEntry(
                self.operational_data.odo,
                self.operational_data.dist, 
                self.operational_data.liters, 
                self.operational_data.bill,
                self.operational_data.car_id
            ))
            self.operational_data = False
            self.bot_state = BotStates.IDLE
            await self.__generic_response(update, context, BotResponses.new_entry_complete)
        else:
            await self.__generic_response(update, context, BotResponses.new_entry_incomplete)
