.. _periodically_schedule:

=======================
periodically schedule
=======================

Interval
-------------

when use ``interval`` in ``tb.restart`` or ``tb.start`` like this ``tb.restart(interval=10)``

it will run tasks periodically with given interval, the unit of interval is ``seconds`` .

if it is omitted, the typology will run only once no matter what ``start_time`` is.


Start time
---------------

start_time option controls when to start typology for the first time.

start_time is a time string with format '%Y-%m-%d %H:%M:%S' (2016-12-03 23:18:19)

when start_time used in ``tb.restart`` or ``tb.start`` like this ``tb.restart(start_time="2016-12-03 20:18:03")``

it means the tpyololgy will start to run at "2016-12-03 20:18:03".



Default value of start_time
-----------------------------

actually, every typoloy has a start_time, if start_time is omitted, the default value is used.

**condition one**

if interval is given and start_time is ommited, the default value is ``math.ceil(time.time() / interval) * interval``,

for example:

presume the time we start typology is ``2016-12-03 20:18:03``.

if interval is 10, the start_time would be ``2016-12-03 20:18:10``

if interval is 5, the start_time would be ``2016-12-03 20:18:05``

if interval is 60, the start_time would be ``2016-12-03 20:19:00``


**condition two**

if start_time and interval both are omitted,

the start_tiem will be ``now`` and run only once


**conditon three**

if interval is given and start_time is less than ``math.ceil(time.time() / interval) - 1) * interval``,
it will be this value, this prevent re-run old task when typology restart.


for example:

presume the time we start typology is ``2016-12-03 20:18:03``.

if start_time is '2016-11:11 12:30:21' and interval is 10,

the start_time would be ``2016-12-03 20:18:00``, this will run immediately and
the second run will be at ``2016-12-03 20:18:10``


if interval is not given, start_time will be its value and just run only once.
