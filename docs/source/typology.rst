==============================
run python code  with rezina
==============================


Start master and workers
------------------------------

In single machine
^^^^^^^^^^^^^^^^^^

start master with

``rezina-cli runmaster -D``

start worker with

``rezina-cli runworker -D``


Multi-machines
^^^^^^^^^^^^^^^

start master with

``rezina-cli runmaster -H master_ip -D``

start worker with

``rezina-cli runworker -H master_ip -WIP worker1_ip -D``

``rezina-cli runworker -H master_ip -WIP worker2_ip -D``


Write python code and put it in workspace
--------------------------------------------

``cd ~/rezina/workspace``

``touch cityweather.py``

sourc code:

::

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


Write typology to run this code in parallel
-----------------------------------------------

``cd ~/rezina/workspace``

``touch weathertypo.py``

source code

::

  #!/usr/bin/env python
  # -*- coding: utf-8 -*-

  from rezina.utils.network import get_ip
  from rezina import TypologyBuilder
  from rezina.backends import Stdout

  from cityweather import get_cities, get_city_weather, one_word_conditions_for_city

  ip = get_ip() # change to your master_ip
  tb = TypologyBuilder(ip, 12345, 'weather_typo')
  tb.add_hydrant(get_cities).add_notch(get_city_weather, 1, 10)
  tb.add_notch(one_word_conditions_for_city, 1, 1)
  tb.add_bocca(Stdout, persistent_mode='stream')

  if __name__ == "__main__":
      tb.restart(interval=10)



note: replace ``ip = get_ip()`` to  ``ip = your_master_ip`` if master_ip is given when start master.


Run code with rezina
-------------------------

run code with

``python weathertypo.py``

**note: it will run the code but not immediately**, it will run like this, presume the time
your run the script is ``2016-12-03 20:18:03``, the first time run is at ``2016-12-03 20:18:10`` and
the second run is at ``2016-12-03 20:18:20`` and next.

if you want run it immediately, use start_time like this:

``tb.restart(start_time="2016-12-03 20:18:03", interval=10")``

the first run will be at ``2016-12-03 20:18:03`` and the second is at ``2016-12-03 20:18:13``

see :ref:`periodically_schedule`


Press ``ctrl-c`` to stop.


manage typology
---------------

you could use console or web console to manage typolog, include start, stop restart
remove, launch more process for one task.


``rezina-cli runconsole -H master_ip``


access http://master_ip:31218 in broswer.
