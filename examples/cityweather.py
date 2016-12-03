#!/usr/bin/evn python


import urllib2
import urllib
import json


def get_cities():
    cities = ['Beijing', 'Berlin', 'New York', 'London', 'Tokyo', 'Paris',
              'Chicago', 'washington', 'Venice', 'Houston']
    return cities


# get city weather data from yahoo weather api
def get_city_weather(city):
    baseurl = "https://query.yahooapis.com/v1/public/yql?"
    yql_query = "select item.condition.text from weather.forecast \
                 where woeid in (select woeid from geo.places(1) \
                 where text='%s')" % (city)
    yql_url = baseurl + urllib.urlencode({'q': yql_query}) + "&format=json"
    result = urllib2.urlopen(yql_url).read()
    data = json.loads(result)
    # because resule from yahoo api does not include the city name, we add it.
    data['city'] = city
    return data


# process diffrent output and convert data to a simple format
def one_word_conditions_for_city(city_weather_result):
    simple_format_data = {}
    simple_format_data['city'] = city_weather_result['city']
    if city_weather_result['query']['results'] is not None:
        weather = city_weather_result['query']['results']['channel']['item']['condition']['text']
    else:
        weather = "Unkonw"  # simplely set unkonw when result is not avaliable
    simple_format_data['weather'] = weather
    return simple_format_data

if __name__ == "__main__":
    for city in get_cities():
        print one_word_conditions_for_city(get_city_weather(city))
