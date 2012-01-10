#!/usr/bin/python
import sys
import argparse
import multiprocessing
from common import *
import termcolor as T
from expt import Expt
from iperf import Iperf
from time import sleep
from host import *

parser = argparse.ArgumentParser(description="Memcached Cluster Test.")
parser.add_argument('--ns',
                    dest="ns",
                    type=int,
                    help="Number of servers.",
                    default=4)

parser.add_argument('--nc',
                    dest="nc",
                    type=int,
                    help="Number of clients.",
                    default=12)

parser.add_argument('--enable', '--enabled',
                    dest="enable",
                    help="Enable isolation.",
                    action="store_true",
                    default=False)

parser.add_argument('--dir',
                    dest="dir",
                    help="Directory to store output.",
                    required=True)

parser.add_argument('--exptid',
                    dest="exptid",
                    help="Experiment ID",
                    default=None)

parser.add_argument('--memaslap',
                    dest="memaslap",
                    help="Memaslap config file",
                    default=None)

parser.add_argument('--traffic',
                    dest="traffic",
                    help="Cross traffic matrix for loadgen.",
                    default=None)

parser.add_argument('--time', '-t',
                    dest="t",
                    type=int,
                    help="Time to run the experiment",
                    default=300)

parser.add_argument('--mtu',
                    dest="mtu",
                    help="MTU of 10G interface",
                    default='1500')

parser.add_argument('--dryrun',
                    dest="dryrun",
                    help="Don't execute experiment commands.",
                    action="store_true",
                    default=False)

parser.add_argument('--active',
                    dest="active",
                    help="Which tenants are active? (udp/mem/udp,mem)",
                    default="udp,mem")

args = parser.parse_args()
MEMASLAP_TID = 1
LOADGEN_TID = 2

class MemcachedCluster(Expt):
    def initialise(self):
        self.hlist.rmmod()
        if self.opts("enable"):
            self.hlist.insmod()

    def prepare_iface(self):
        h = self.hlist
        h.set_mtu(self.opts("mtu"))

        if self.opts("enable"):
            h.prepare_iface()
            h.create_ip_tenant(MEMASLAP_TID)
            h.create_ip_tenant(LOADGEN_TID)

    def memaslap(self, host, dir="/tmp"):
        time = int(self.opts("t")) - 5
        config = self.opts("memaslap")
        active = self.opts("active")
        if config is None:
            return
        if "mem" not in active:
            return
        servers = []
        for h in self.hs.lst:
            ip = h.get_10g_ip()
            if self.opts("enable"):
                ip = h.get_tenant_ip(MEMASLAP_TID)
            servers.append("%s:11211" % ip)
        servers = ",".join(servers)

        cmd = "mkdir -p %s; " % dir
        cmd += "memaslap -s %s " % servers
        cmd += "-S 1s -t %ss " % time
        cmd += "-c 512 -T 4 -B -F %s " % config
        cmd += " > %s/memaslap.txt" % dir
        host.cmd_async(cmd)

    def loadgen(self, host, traffic=None, dir="/tmp"):
        if traffic is None:
            return
        active = self.opts("active")
        if "udp" not in active:
            return
        out = os.path.join(dir, "loadgen.txt")
        LOADGEN = "/root/vimal/exports/loadgen "
        ip = host.get_10g_ip()
        if self.opts("enable"):
            ip = host.get_tenant_ip(LOADGEN_TID)
        cmd = "%s -i %s " % (LOADGEN, ip)
        cmd += " -l 12345 -p 500000 -f %s > %s" % (traffic, out)
        host.cmd_async(cmd)

    def loadgen_start(self):
        if "udp" not in self.opts("active"):
            return
        procs = []
        for h in self.hlist.lst:
            ip = h.get_10g_ip()
            if self.opts("enable"):
                ip = h.get_tenant_ip(LOADGEN_TID)
            sleep(2)
            p = Popen("nc -nzv %s 12345" % ip, shell=True)
            procs.append(p)
        for p in procs:
            p.wait()
        return

    def start(self):
        # num servers, num clients
        ns = self.opts("ns")
        nc = self.opts("nc")
        dir = self.opts("dir")
        xtraffic = self.opts("traffic")

        assert(ns + nc <= len(host_ips))
        hservers = HostList()
        hclients = HostList()
        hlist = HostList()

        for i in xrange(ns):
            ip = pick_host_ip(i)
            h = Host(ip)
            hservers.append(h)
            hlist.append(h)
            self.log(T.colored(ip, "green"))

        for i in xrange(ns, ns+nc):
            ip = pick_host_ip(i)
            h = Host(ip)
            hclients.append(h)
            hlist.append(h)
            self.log(T.colored(ip, "yellow"))

        self.hs = hservers
        self.hc = hclients
        self.hlist = hlist
        hlist.set_dryrun(self.opts("dryrun"))
        self.initialise()
        # Automatically initialised by the module
        #hlist.perfiso_set("IsoAutoGenerateFeedback", "1")
        #hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8500)
        #hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
        self.prepare_iface()

        hservers.start_memcached()
        sleep(2)
        for h in hclients.lst:
            self.memaslap(h, dir)
        hlist.start_monitors(dir)

        for h in hlist.lst:
            self.loadgen(h, xtraffic, dir)
        self.loadgen_start()

    def stop(self):
        self.hlist.killall("memslap memcached loadgen")
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"), self.opts("exptid"))
        return

MemcachedCluster(vars(args)).run()