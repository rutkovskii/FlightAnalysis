#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os
import pandas as pd
import re
from datetime import datetime
import matplotlib.pyplot as plt
import os.path
#from config import TOKEN
import logging

TOKEN = os.environ.get('TOKEN')

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InputMediaPhoto
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

#GENDER, PHOTO, LOCATION, BIO = range(4)
USER_INPUT = range(1)

#Uploaded csv's to Cloudinary.com in order to use the data in Heroku Deployment
FLIGHTS = pd.read_csv('https://res.cloudinary.com/dnvoqaxlg/raw/upload/v1648767306/all_flights_bcvdb7.csv',index_col=0)
INT_AIRPORTS = pd.read_csv('https://res.cloudinary.com/dnvoqaxlg/raw/upload/v1648767318/international_airports_ocls7g.csv',index_col=0)
RU_AIRPORTS = pd.read_csv('https://res.cloudinary.com/dnvoqaxlg/raw/upload/v1648767325/russian_airports_h7aef4.csv',index_col=0)
#logger.info(FLIGHTS)
FLIGHTS['day'] = pd.to_datetime(FLIGHTS['day'], format="%Y/%m/%d").dt.date

#print(FLIGHTS)
#print(RU_AIRPORTS)
#print(INT_AIRPORTS)

def pop_printer(df, option: str):
    """Prints most travelled destinations or countries"""
    reply_pop = ""
    i = 1
    for index, row in df.iterrows():
        if pd.isnull(row['Country']):
            continue

        if i == 1: suffix = "st"
        elif i == 2: suffix = "nd"
        elif i == 3: suffix = "rd"
        elif i == 4 or i == 5: suffix = "th"


        if option == "dest":
            reply_pop += f"\n—{i}{suffix} most traveled destination is {row['Airport']}, {row['Country']} with {row['Amount']} flight(s)."
        elif option == "country":
            reply_pop += f"\n—{i}{suffix} most traveled is country {row['Country']} with {row['Amount']} flight(s)."

        i += 1
        if i == 6: break

    return reply_pop

def pop_df_cleaner(df, option):
    """Creates lists with the most travelled destinations or countries to be plotted"""
    x, y = [], []
    i = 1
    for index, row in df.iterrows():

        if pd.isnull(row['Country']):
            continue

        if option == "dest":
            if pd.isnull(row['Airport']):
                continue

        y.append(row['Amount'])
        if option == "country":
            x.append(row['Country'])
        elif option == "dest":
            x.append(row["Airport"] + ', ' + row['Country'])

        i += 1
        if i == 6: break

    return x, y

def create_plt(df, option):
    """Creates the barplot with the most travelled destinations or countries"""
    x, y = pop_df_cleaner(df, option)

    fig = plt.figure()

    if option == "dest":
        plt.title('Destination Airports Vs Amount of Flights', fontsize=14, pad=20)
        plt.xlabel('Destination Airports', fontsize=11)

    elif option == "country":
        plt.title('Country Vs Amount of Flights', fontsize=14, pad=20)
        plt.xlabel('Country', fontsize=11)

    plt.ylabel('Amount of Flights', fontsize=10)
    plt.xticks(range(0,len(x)),x, fontsize=8, rotation=45)
    plt.margins(y=0.2)
    plt.bar(x=x, height=y)

    if option == "dest":
        name = "dest"
    elif option == "country":
        name = "country"
    plt.savefig(f'{name}.png', bbox_inches='tight')


def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Hi! My name is FlightAnalyzer Bot.\n'
        'I can send flight statistics for a certain day and airport in Russia from 1st of'
        'January, 2022 until 28th of February, 2022.\n\n'
        'Send /cancel to stop talking to me.\n\n'
        'Type Date and Airport in this format: "dd mm yyyy, Airport Name"\n'
        'For example: "01 January 2022, Sheremetyevo"\n\n',
    )
    return USER_INPUT


def ask_user(update: Update, context: CallbackContext):
    """Return statistics for given day and airport"""
    user = update.message.from_user
    logger.info("Input of %s: %s", user.first_name, update.message.text)

    RU_AIRPORTS_2 = RU_AIRPORTS.copy()


    user_date_status, user_airport_status = False, False
    while not user_date_status and not user_airport_status:
        user_date_status, user_airport_status = False, False
        # Testing Purposes 
        # user_input = "01 01 2022, Sheremetyevo" # "31 January 2022 Sheremetyevo"

        # Separate date and airport
        elements =  update.message.text.split(',')

        # Not comma separated
        if len(elements) < 2:
            update.message.reply_text('You forgot to add comma after date. Type /start and then enter Date and Airport Again!')
            return ConversationHandler.END

        # Missing airport or date
        if (elements[0] == "") or (elements[1] == ""):
            update.message.reply_text('You forgot to add date or airport. Type /start and then enter Date and Airport Again')
            return ConversationHandler.END

        # Cleaning date
        user_date = elements[0]
        user_date.replace('-', ' ').replace('/', ' ')

        # Getting Date from User input
        pattern = r"\d{2} \d{2} \d{4}" + "|\d{2} \w+ \d{4}"
        match = re.search(pattern, user_date)

        # If invalid Date
        if not match:
            update.message.reply_text('You entered invalid date. Type /start and then enter Date and Airport Again')
            return ConversationHandler.END

        # Extracting all elements in the string
        month = user_date.split(' ')[1]

        # Converting to data
        if month.isdigit():
            date = datetime.strptime(match.group(), '%d %m %Y').date()
        else:
            date = datetime.strptime(match.group(), '%d %B %Y').date()

        # print(date)
        if date:
            user_date_status = True

        # Airport
        user_airport = elements[1].strip()

        # Find ICAO code for airport
        ru_port = RU_AIRPORTS[RU_AIRPORTS["Airport"].str.contains(user_airport)]

        if ru_port.empty:
            update.message.reply_text('You entered incorrect airport name. Type /start and then enter Date and Airport Again')
            return ConversationHandler.END

        icao = ru_port.iloc[0][1]

        if icao:
            # can be a method

            # cleaning on the day of flight
            ru_port_flights = FLIGHTS.loc[FLIGHTS['day'] == date]
            # cleaning on origin Russian Airport and removing from-into flights
            ru_port_flights = ru_port_flights.loc[ru_port_flights['origin'] == icao]
            ru_port_flights = ru_port_flights.loc[ru_port_flights['destination'] != icao]
            ################## Statistics ##################

            # 1
            num_flights = len(ru_port_flights)  # Number of flights from airport
            if num_flights > 0:
                user_airport_status = True

            # df with unique destinations (not to use because does not have countries)
            unique_dests_df = ru_port_flights["destination"].value_counts().rename_axis('ICAO').reset_index(
                name='Amount')

            # 2
            num_unique_dests = unique_dests_df.shape[0]  # alternatively len(unique_dests_df)

            # 3
            # Unique destinations
            most_visited_dests = INT_AIRPORTS.merge(unique_dests_df, on='ICAO', how='right')
            most_visited_dests = most_visited_dests.set_index('ICAO')
            RU_AIRPORTS_2 = RU_AIRPORTS_2.set_index('ICAO')
            most_visited_dests.update(RU_AIRPORTS_2)
            most_visited_dests.reset_index(inplace=True)
            RU_AIRPORTS_2.reset_index(inplace=True)
            most_visited_dests = most_visited_dests[["ICAO", "Country", "Airport", "Amount"]]

            # Unique countries (omitting NaNs)
            most_visited_countries = most_visited_dests.loc[most_visited_dests["Country"] != "Russia"].dropna().copy()
            #print(most_visited_countries['Country'].unique())
            countries, amounts = [],[]
            for country in most_visited_countries['Country'].unique():
                countries.append(country)
                amount = 0
                for index, row in most_visited_countries.iterrows():
                    if country == row['Country']:
                        amount += row['Amount']
                amounts.append(amount)

            most_visited_countries = pd.DataFrame({'Country':countries,'Amount':amounts})
            #most_visited_countries = most_visited_countries['Country'].value_counts().rename_axis('Country').reset_index(name='Amount')

            # 4
            num_unique_countries = most_visited_countries.shape[0]

            ################## Output ##################
            # 1
            reply_text = f"*{num_flights} flight(s) were made from {ru_port.iloc[0][0]} on {date}.\n"
            if num_flights > 0:
                # 2
                reply_text += f"*To {num_unique_dests} unique destination(s)."
                # 3
                reply_text += pop_printer(df=most_visited_dests, option="dest")
                # 3.1
                if num_unique_dests > 2:
                    create_plt(most_visited_dests, option="dest")
                # 4
                reply_text += f"\n\n*To {num_unique_countries} unique countries."
                # 5
                reply_text += pop_printer(df=most_visited_countries, option="country")
                # 5.1
                if num_unique_countries > 2:
                    create_plt(most_visited_countries, option="country")
                    
                media_group = []
                if os.path.exists('dest.png'):
                    media_group.append(InputMediaPhoto(open('dest.png', 'rb')))
                if os.path.exists('country.png'):
                    media_group.append(InputMediaPhoto(open('country.png', 'rb')))

                update.message.reply_text(reply_text)
                if media_group:
                    #update.message.reply_photo(photo=open('dest.png', 'rb'))
                    update.message.reply_media_group(media=media_group)

                if os.path.exists('dest.png'):
                    os.remove('dest.png')
                if os.path.exists('country.png'):
                    os.remove('country.png')

            update.message.reply_text('\nThank you for using me! To use again, press /start.\n')
            return ConversationHandler.END






def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Thank you for using me!', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USER_INPUT:[MessageHandler(Filters.text, ask_user)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    #ou press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully. Run the bot until y
    updater.idle()


if __name__ == '__main__':
    main()
