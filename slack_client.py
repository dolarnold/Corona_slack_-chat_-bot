# importing modules
import argparse
import datetime
import json
import logging

import requests
from tabulate import tabulate

from slack_client import slacker

FORMAT = '[%(asctime)-15s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG, filename='bot.log', filemode='a')

URL = "https:https://www.worldometers.info/coronavirus/"
SHORT_HEADERS = ['Country', 'Total Cases', 'New Cases', 'Total Deaths', 'New Deaths', 'Total Recovered', 'Active Cases',
                 'Critical Cases', '1m pop']
FILE_NAME = 'corona_world_data.json'
extract_contents = lambda row: [x.text.replace('\n', '') for x in row]


def save(x):
    with open(FILE_NAME, 'w') as f:
        json.dump(x, f)


def load():
    res = {}
    with open(FILE_NAME, 'r') as f:
        res = json.load(f)
    return res


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--states', default=',')
    args = parser.parse_args()
    interested_states = args.states.split(',')

    current_time = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    info = []

    try:
        response = requests.get(URL).content
        soup = BeautifulSoup(response, 'html.parser')
        header = extract_contents(soup.tr.find_all('th'))

        stats = []
        all_rows = soup.find_all('tr')
        for row in all_rows:
            stat = extract_contents(row.find_all('td'))
            if stat:
                if len(stat) == 9:
                    # last row
                    stat = ['', *stat]
                    stats.append(stat)
                elif any([s.lower() in stat[1].lower() for s in interested_states]):
                    stats.append(stat)

        past_data = load()
        cur_data = {x[1]: {current_time: x[2:]} for x in stats}

        changed = False

        for country in cur_data:
            if country not in past_data:
                # new state has emerged
                info.append(f'NEW_COUNTRY {country} got corona virus: {cur_data[country][current_time]}')
                past_data[country] = {}
                changed = True
            else:
                past = past_data[country]['latest']
                cur = cur_data[country][current_time]
                if past != cur:
                    changed = True
                    info.append(f'Change for {country}: {past}->{cur}')

        events_info = ''
        for event in info:
            logging.warning(event)
            events_info += '\n - ' + event.replace("'", "")

        if changed:
            # override the latest one now
            for country in cur_data:
                past_data[country]['latest'] = cur_data[country][current_time]
                past_data[country][current_time] = cur_data[country][current_time]
            save(past_data)

            table = tabulate(stats, headers=SHORT_HEADERS, tablefmt='psql')
            slack_text = f'Please find CoronaVirus Country wide summary:\n{events_info}\n```{table}```'
            slacker()(slack_text)
    except Exception as e:
        logging.exception('oops, corono script failed.')
        slacker()(f'Exception occured: [{e}]')
