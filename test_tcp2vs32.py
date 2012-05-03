from expt import Expt
from host import *
from iperf import Iperf
from time import sleep
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--dir',
                        required=True,
                        dest="dir")

    parser.add_argument('--enable', '--enabled',
                        action="store_true",
                        dest="enabled",
                        help="Enable perfisolation",
                        default=False)

    parser.add_argument('--time', '-t',
                        type=int,
                        dest="time",
                        help="Time to run expt",
                        default=120)

    parser.add_argument('--wtcp',
                        dest="wtcp",
                        type=int,
                        help="Weight of the TCP flow.",
                        default=2)

    parser.add_argument('--vqrate',
                        dest="vqrate",
                        help="VQ drain rate.",
                        default="9000")

    args = parser.parse_args()

class Tcp2Vs32(Expt):
    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        h3 = Host("10.0.1.3")
        self.hlist = HostList(h1, h2, h3)
        hlist = self.hlist

        hlist.prepare_iface()
        hlist.configure_rps()
        hlist.rmmod()
        if self.opts("enabled"):
            hlist.insmod()
            self.log("Creating two tenants")
            #h1.create_tcp_tenant(server_ports=[5001], tid=1)
            #h1.create_tcp_tenant(server_ports=[5002], tid=2)
            #h2.create_tcp_tenant(server_ports=[5001], tid=1)
            #h3.create_tcp_tenant(server_ports=[5002], tid=2)
            h1.create_ip_tenant(tid=1, weight=self.opts("wtcp"))
            h1.create_ip_tenant(tid=2)

            h2.create_ip_tenant(tid=1)
            h3.create_ip_tenant(tid=1)

        if self.opts("enabled"):
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts("vqrate"))
            hlist.perfiso_set("IsoAutoGenerateFeedback", 1)
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
        hlist.start_monitors(self.opts("dir"), 1e3)

        self.procs = []
        # Start iperf servers
        for p in [5001, 5002]:
            iperf = Iperf({'-p': p})
            server = iperf.start_server(h1)
            self.procs.append(server)

        sleep(1)
        # Start 1 TCP connection from h2 to h1
        client = Iperf({'-p': 5001,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-P': 1})
        if self.opts("enabled"):
            client.opts["-c"] = h1.get_tenant_ip(1)
        client = client.start_client(h2)
        self.procs.append(client)

        # Start 32 TCP from h3 to h1
        client = Iperf({'-p': 5002,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-P': 32})
        if self.opts("enabled"):
            client.opts["-c"] = h1.get_tenant_ip(2)
        client = client.start_client(h3)
        self.procs.append(client)

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"))
        for p in self.procs:
            p.kill()
        self.hlist.killall()


if __name__ == "__main__":
    Tcp2Vs32(vars(args)).run()
