
import common

class Iperf:
    def __init__(self, opts):
        self.opts = opts

    def start_server(self, host):
        cmd = "iperf -s -p %d" % (self.opts.get('-p', 5001))
        return common.cmd_host_async(host, cmd)

    def start_client(self, host):
        server_ip = self.opts.get('-c', '')
        port = self.opts.get('-p', '')
        parallel = self.opts.get('-P', '')
        t = self.opts.get('-t', 30)
        cmd = "iperf -c %s -p %s -P %d -t %d" % (server_ip, port, parallel, t)
        return common.cmd_host_async(host, cmd)
