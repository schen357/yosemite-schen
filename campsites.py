#!/usr/bin/env python
import argparse
import copy
import requests
import calendar

import urllib
from urlparse import parse_qs
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Hardcoded list of campgrounds I'm willing to sleep at
PARKS = {
    '70925': 'UPPER PINES',
    '70928': 'LOWER PINES',
    '70927': 'NORTH PINES',
#    '73635': 'STANISLAUS',
#    '70926': 'TUOLOMNE MEADOWS'
# only interested in pines campgrounds
}

# Sets the search location to yosemite
LOCATION_PAYLOAD = {
    'currentMaximumWindow': '12',
    'locationCriteria': 'yosemite',
    'interest': '',
    'locationPosition': '',
    'selectedLocationCriteria': '',
    'resetAllFilters':    'false',
    'filtersFormSubmitted': 'false',
    'glocIndex':    '0',
    'googleLocations':  'Yosemite National Park, Yosemite Village, CA 95389, USA|-119.53832940000001|37.8651011||LOCALITY'
}

# Sets the search type to camping
CAMPING_PAYLOAD = {
    'resetAllFilters':  'false',
    'filtersFormSubmitted': 'true',
    'sortBy':   'RELEVANCE',
    'category': 'camping',
    'selectedState':    '',
    'selectedActivity': '',
    'selectedAgency':   '',
    'interest': 'camping',
    'usingCampingForm': 'true'
}

# Runs the actual search
PAYLOAD = {
    'resetAllFilters':   'false',
    'filtersFormSubmitted': 'true',
    'sortBy':   'RELEVANCE',
    'category': 'camping',
    'availability': 'all',
    'interest': 'camping',
    'usingCampingForm': 'false'
}


BASE_URL = "https://www.recreation.gov"
UNIF_SEARCH = "/unifSearch.do"
UNIF_RESULTS = "/unifSearchResults.do"

def findCampSites(args):
    payload = generatePayload(args['month'], args['year'], args['day_of_week'], args['num_nights'])

    content_raw = sendRequest(payload)
    html = BeautifulSoup(content_raw, 'html.parser')
    sites = getSiteList(html)
    return sites

#def getNextDay(date):
#    date_object = datetime.strptime(date, "%Y-%m-%d")
#    next_day = date_object + timedelta(days=1)
#    return datetime.strftime(next_day, "%Y-%m-%d")

def formatDate(date):
#   date_object = datetime.strptime(date, "%Y-%m-%d")
    date_formatted = datetime.strftime(date, "%a %b %d %Y")
    return date_formatted

def generateDates(month, year, day_of_week):
    monthWeeks = calendar.Calendar().monthdatescalendar(year, month)
    dayOfWeek = list(calendar.day_name).index(day_of_week)

    start_dates = []

    # create set of start dates for month for given day of week
    for i in range(len(monthWeeks)):
        start_dates.append(monthWeeks[i][dayOfWeek])

    return start_dates

def generatePayload(month, year, day_of_week, num_nights):
    payload = copy.copy(PAYLOAD)

    start_dates = generateDates(month, year, day_of_week)

    payload['arrivalDate'] = formatDate(start_dates[1])
    end_date = start_dates[1] + timedelta(days=num_nights)
    payload['departureDate'] = formatDate(end_date)

    return payload

def getSiteList(html):
    sites = html.findAll('div', {"class": "check_avail_panel"})
    results = []
    for site in sites:
        if site.find('a', {'class': 'book_now'}):
            get_url = site.find('a', {'class': 'book_now'})['href']
            # Strip down to get query parameters
            get_query = get_url[get_url.find("?") + 1:] if get_url.find("?") >= 0 else get_url
            if get_query:
                get_params = parse_qs(get_query)
                siteId = get_params['parkId']
                if siteId and siteId[0] in PARKS:
                    results.append("%s, Booking Url: %s" % (PARKS[siteId[0]], BASE_URL + get_url))
    return results

def sendRequest(payload):
    with requests.Session() as s:

        s.get(BASE_URL + UNIF_RESULTS, verify=False) # Sets session cookie
        s.post(BASE_URL + UNIF_SEARCH, LOCATION_PAYLOAD, verify=False) # Sets location to yosemite
        s.post(BASE_URL + UNIF_SEARCH, CAMPING_PAYLOAD, verify=False) # Sets search type to camping

        resp = s.post(BASE_URL + UNIF_SEARCH, payload, verify=False) # Runs search on specified dates
        if (resp.status_code != 200):
            raise Exception("failedRequest","ERROR, %d code received from %s".format(resp.status_code, BASE_URL + SEARCH_PATH))
        else:
            return resp.text

# SC updating to make command input a month and day(s) of week so that script can check any weekend of a month for instance
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, type=int, help="Month [MM] with no leading 0s e.g. Jan = 1")
    parser.add_argument("--year", required=True, type=int, help="Year [YYYY]")
    parser.add_argument("--day_of_week", required=True, type=str, help="First night of week e.g. Friday")
    parser.add_argument("--num_nights", type=str, help="Consecitive number of nights desired e.g. 2")
#    parser.add_argument("--end_date", type=str, help="End date [YYYY-MM-DD]")

    args = parser.parse_args()
    arg_dict = vars(args)
    #if 'end_date' not in arg_dict or not arg_dict['end_date']:
    #    arg_dict['end_date'] = getNextDay(arg_dict['start_date']) #if no end date, use next day from start date
    if 'num_nights' not in arg_dict or not arg_dict['num_nights']:
        arg_dict['num_nights'] = 1 # set to 1 night if no num nights given

    sites = findCampSites(arg_dict)
    if sites:
        for site in sites:
            print site + \
                "&arrivalDate={}&departureDate={}" \
                .format(
                        urllib.quote_plus(formatDate(arg_dict['start_date'])),
                        urllib.quote_plus(formatDate(arg_dict['end_date'])))
