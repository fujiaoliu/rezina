Rezina
=======

rezina is a scalable, distributed and easy to use system for executing python code in parallel across multiple processors or many machines.  It provides a simple way to make parallel programming in python more easier, flexible and scalable and shipped with  features like periodically schedule, load balance, fail tolerate, dynamically add tasks and save results to backend.

why use rezina?
================

Consider this task, I want to gather weather data of ten cities from yahoo weather api. I wrote a scirpt `cityweather.py` to do this.
::
   liufujiaodeMacBook-Pro:workspace liufujiao$ time python cityweather.py
   {'city': 'Beijing', 'weather': u'Mostly Sunny'}
   {'city': 'Berlin', 'weather': u'Partly Cloudy'}
   {'city': 'New York', 'weather': u'Mostly Clear'}
   {'city': 'London', 'weather': u'Mostly Cloudy'}
   {'city': 'Tokyo', 'weather': u'Mostly Sunny'}
   {'city': 'Paris', 'weather': u'Mostly Cloudy'}
   {'city': 'Chicago', 'weather': u'Partly Cloudy'}
   {'city': 'washington', 'weather': u'Clear'}
   {'city': 'Venice', 'weather': u'Breezy'}
   {'city': 'Houston', 'weather': u'Breezy'}

   real	0m18.726s
   user	0m0.080s
   sys	0m0.034s

The whole process of fetching data take 20s and we could think one city takes 2s on average.

Now here is the problem, what if I want to get the ten weather data every 10 seconds so I could always know the least weather?  this requires all data should be fetched in 10s.

One simple way to do this is we could start more threads (or processes) to fetch data in parallel and implement logic to run periodically.

Problem again, now I want to get weather data of 50,000 cities so I can build a weather website to provide weather conditions for my user, how to do it?

One server could not launch 10,000 threads. maybe we could split all cites into several parts and run every part with threads on different servers, but this kind of solution need consider the following problems.

* what if one or more servers down?
* what if we want to add or remove some cites?
* what if we want to launch more processes for time consuming logic?
* what if we want to change the fetch interval from 10s to 5s.
* what if we want to save data in another backend?
* …

We need a easier and flexible way to execute tasks in parallel without pay much attentions on these problems and make us focus only on our business logic. this is the motivation of rezina project.

See Quick Guide for how rezina do this.

Support
==========
**Python**

* python2.7
* python3.5

**OS**

* OS X
* Linux

Dependencies
=============

rezina requires `pyzmq <https://github.com/zeromq/pyzmq>`_ for message transports.

 pyzmq is python bindings for `ØMQ <http://zeromq.org/>`_. ØMQ is a lightweight and fast messaging implementation.

Installaion
=============


You can install reizna either via the Python Package Index (PyPI) or from source.

To install using pip:

``pip install rezina``

Downloading and installing from source
---------------------------------------

Before install rezina, `building-and-installation <https://github.com/zeromq/pyzmq#building-and-installation>`_
pyzmq first.

After pyzmq installed, download the latest version of rezina from PyPI:

http://pypi.python.org/pypi/rezina

and install it by doing the following:

``pip install /path/to/rezina-0.x.y.tar.gz``

or

``tar xvfz rezina-0.x.y.tar.gz``

``cd rezina-0.x.y``

``python setup.py install``

Quick Guide
==============

Start rezina 
---------------

Once rezina is installed, you can run

``rezina-cli runmaster -H master_ip``

to start rezina master.


After master started, you could run

``rezina-cli runworker -H master_ip -WIP worker_ip``

to start rezina worker.

 we could use `-D` to run master as daemon and `-W` to specify a new workspace. please see `startup settings <http://rezina.readthedocs.io/en/latest/startupsettings.html#startup-setttings>`_ for starting rezina correctly.

Example cityweather
--------------------

cityweather code
^^^^^^^^^^^^^^^^^

script name: ``cityweather.py``

put this script into rezina workspace (``~/rezina/workspace`` by default, use -W /path/to/your/workspace when starting master if you want to change it)

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



Build a typology to run cityweather with rezina
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

script name: ``weathertypo.py``

put it info rezina workspace (``~/rezina/workspace`` by default)

 you could regard hydrant, notch, bocca as input, filter, output respectively for now. A typology looks like `input | filter1 | filter2 | output` in shell. check the Documentation for more info.


run ``get_city_weather`` function with 2 processes and every process run 5 threads and each thread fetch one city.

run ``one_word_conditions_for_city`` function with 1 process with 1 thread because it is not time consuming one.

::

    #!/usr/bin/env python

    from rezina import TypologyBuilder
    from rezina.backends import Stdout

    from cityweather import get_cities, get_city_weather, one_word_conditions_for_city

    ip = master_ip  # your master_ip
    tb = TypologyBuilder(ip, 12345, 'weather_typo2')
    tb.add_hydrant(get_cities)
    tb.add_notch(get_city_weather, 2, 5)
    tb.add_notch(one_word_conditions_for_city, 1, 1)
    tb.add_bocca(Stdout, persistent_mode='stream')

    if __name__ == "__main__":
        tb.restart(start_time="2016-12-03 20:18:10", interval=10)


replace ``ip = master_ip`` to ``ip = your_real_master_ip``, for example ``ip = '127.0.0.1'``. 
you could change ``start_time`` in ``tb.restart``, time string format ``%Y-%m-%d %H:%M:%S``
 
see `periodically schedule <http://rezina.readthedocs.io/en/latest/periodicallyschedule.html#periodically-schedule>`_

run typology
^^^^^^^^^^^^

rezina typology file is just a python script, run it with

``python weathertypo.py`` or ``./weathertypo.py``` and you get the results. 

Press ``ctrl-c`` to stop.

You could also save the results of your typology to another backend rather than print them.

See documentation for more details.


rezina console
----------------

rezina provides command line tool and web console to manage master, workers, typologies.

you could run

```rezina-cli runconsole -H master_ip``

 to start cml or access ``master_ip:31218`` to see web console.

Documentation
================

See http://rezina.readthedocs.io/en/latest/ for more info.


Rezina-Web
===========

rezina-web is the web console of rezina powered by Angular2, Webpack.js, Angular Material2.

see `rezina-web <https://github.com/fujiaoliu/rezina-web>`_  project.


.. image:: https://cloud.githubusercontent.com/assets/1925552/20864262/8ebefafa-ba24-11e6-8a3d-35fe271d43c3.png
    :width: 1280px
    :align: center

