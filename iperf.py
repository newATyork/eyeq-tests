
from host import Host
import common

class Iperf:
    def __init__(self, opts):
        self.opts = opts

    def start_server(self, host):
        cmd = "iperf -s -p %d" % (self.opts.get('-p', 5001))
        if self.opts.get('-u', False):
            cmd += " -u"
        h = Host(host)
        h.cmd_async(cmd)
        return self

    def start_client(self, host):
        server_ip = self.opts.get('-c', '')
        port = self.opts.get('-p', '')
        parallel = self.opts.get('-P', '')
        t = self.opts.get('-t', 30)
        cmd = "iperf -c %s -p %s -P %d -t %d" % (server_ip, port, parallel, t)
        cmd += " > /tmp/iperf-%s 2>&1" % server_ip
        if self.opts.get('-b', False): # -b implies UDP, which is weird
            cmd += " -b %s" % self.opts.get('-b')
        h = Host(host)
        h.cmd_async(cmd)
        return self

    def kill(self):
        pass
