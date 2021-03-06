#!/usr/bin/env python
import acos_client as acos
import sys
import os

cmd = sys.argv[1]

a10IP = os.environ["a10IP"]
a10mgmtPort = os.environ["a10mgmtPort"]
a10proto = os.environ["a10mgmtProto"]

# Create list of dependent service tiers
dependencies = os.environ["CliqrDependencies"].split(",")
# NOTE: THIS SCRIPT ONLY SUPPORTS THE FIRST DEPENDENT TIER!!!


# Set the new server list from the CliQr environment
serverIps = os.environ["CliqrTier_" + dependencies[0] + "_IP"].split(",")

pool = 'pool' + os.environ['parentJobId']
vip = 'vip' + os.environ['parentJobId']
# healthMonitor = 'hm'+os.environ['parentJobId']

c = acos.Client(a10IP, acos.AXAPI_21, 'admin', 'welcome2cliqr', port=a10mgmtPort, protocol=a10proto)

if cmd == "start":
    # Make a list out of the IP addresses of the web server tier.
    print serverIps

    # Create pool and add to VIP.
    c.slb.service_group.create(pool, c.slb.service_group.TCP, c.slb.service_group.ROUND_ROBIN)

    # Create and apply a health check for the pool
    # c.slb.hm.create(healthMonitor, c.slb.hm.HTTP, 5, 5, 5, 'GET', '/', '200', 80)

    # Apply a ping health-check to pool
    # c.slb.service_group.update(pool, health_monitor=ping)

    # Add each web server IP as a real server, then add it to the pool.
    for server in serverIps:
        serverName = 's' + server
        c.slb.server.create(serverName, server)
        c.slb.service_group.member.create(pool, serverName, 80)

    # Create a VIP
    c.slb.virtual_server.create(vip, a10IP)

elif cmd == "reload":
    # All these next ten lines just to get the current running LB pool

    # Initialize an empty list as the current pool
    currPool = {}
    # Get all the members in the current pool from API
    r = c.slb.service_group.get(pool)

    # Add each member's IP address to the current pool list.
    for member in r['service_group']['member_list']:
        # Get a reference to this server.
        s = c.slb.server.get(member['server'])

        ip = str(s['server']['host'])
        name = str(s['server']['name'])

        # Convert the server's IP (host) to str, then add to current pool list.
        currPool[ip] = name

    ################

    # For each server in the new serverIps, add it to addServers if it's not in the current pool
    addServers = [server for server in serverIps if server not in currPool.keys()]

    # For each server in the currPool, add it to removeServers if it's not in serverIps
    removeServers = [server for server in currPool.keys() if server not in serverIps]

    for server in addServers:
        serverName = 's' + server
        c.slb.server.create(serverName, server)
        c.slb.service_group.member.create(pool, serverName, 80)

    for server in removeServers:
        c.slb.server.delete(currPool[server])

elif cmd == "stop":
    c.slb.virtual_server.delete(vip)
    c.slb.service_group.delete(pool)

    for server in serverIps:
        serverName = 's' + server
        c.slb.server.delete(serverName)
