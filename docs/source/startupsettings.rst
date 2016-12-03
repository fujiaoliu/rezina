==================
Startup setttings
==================


Master
------

``rezina-cli runmaster``

options:

``-H or --host``, the ip of machine running rezina master, the default value is IPv4 address of
fully qualified domain name, If name is omitted or empty, it is ``127.0.0.1``.

``-P or --port``, master_port, **12345** by default.

``-D``, run master as a daemon process, example: ``rezina-cli runmaster -D``

``-L or --log_dir``, rezina log directory, you should use **absolutely path** for this option.
every typology has its own log file which name is the same with typology name, you could find the error
which tells why typology does not run correctly. it is ``~/rezina/log`` by default.

``-W or --worksapce``, workerspace directory.  you should use **absulotely path** for this option. ``~/rezina/workerspace`` by default.
when we run a python function in a module with rezina, it is actually running on
rezina workers, therefore workers must have the module and then import the function and run it.

To do this, rezina will send all files under workspace directory to workers, so you should put python files into workspace directory.
but this does not mean we need put all depandencies into workspace, if you imported some third-part python libs in your module,
there is no need to put them into workspace too, just make sure all workers also installed these libs
and can be imported by python. when typology run, workers will import those libs as python dose and run your function.


``-HP or --http_port``, the port for access web console, **31218** by default,
after master started, you could open broswer and go to master_ip:31218 to see the web console.

``-R`` refresh (or recreate) DB file, it is ``False`` by defaut, this is a **error prone** option,
rezina master is a sevice set, and every service need a tcp address for communcating with workers, after the first time rezina master started,
actually all tcp_address of services include master_ip and master_port are stored in db,
if rezina master stoped (killed by accident or poweroff), when we re-run master without -R option, it will use those saved tcp_addresses
and then master can still talk to workers.

**If your really want change master_ip and master_port**, **stop all workers first and restart master with -R option**.

this option is only effect tcp_address of service, the other options(except master_ip and master_port) take effective every time re-run master


Worker
-------

``rezina-cli runworker``

options:

``-H or --host``, master_ip

``-P or --port``, master_port.  (default 12345)

``-WIP or --worker_ip``, worker_ip, this is the ip of machine used to connect master.

``-D`` run worker as a daemon process, it is False by default


Console
---------

``rezina-cli runconsole``

options:

``-H or --host``, master_ip

``-P or --port``, master_port  (default 12345)

you could use console to see settings


start console with ``rezina runconsole``

run ``list settings`` in console


examples
-------------

**single machine**

``rezina-cli runmaster -D``

``rezian-cli runworker -D``

``rezina-cli runconsole``


**multi-workers**

``rezina-cli runmaster -H 192.168.1.100 -P 11111 -D -L /path/to/log -W /my/exist/dir/contain/python``


``rezina-cli runworker -H 192.168.1.100 -P 11111 -D -WIP 192.168.1.101``

``rezina-cli runworker -H 192.168.1.100 -P 11111 -D -WIP 192.168.1.102``

``rezina-cli runworker -H 192.168.1.100 -P 11111 -D -WIP 192.168.1.103``

``rezina-cli runconsole -H 192.168.1.100 -P 11111``
