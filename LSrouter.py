import sys
from collections import defaultdict
from router import Router
from packet import Packet
from link import Link
import networkx as nx

class Table:
    """Forwarding Table Entry"""
    def __init__(self, _dest_address, _cost, _next_hop):
        self.destination = _dest_address
        self.cost = _cost
        self.next_hop = _next_hop

class LinkStatePacket:
    """Link State for all Routers"""
    def __init__(self, _router, _sqno, _neighbours):
        self.src_router = _router # source router from which the links info was received
        self.seq_no = _sqno
        self.neighbors = _neighbours # list of neighbours(links)

class LSrouter(Router):
    """Link state routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        self.sq_nb = 0 # Initialize the sequence number for this router
        self.routing_table = {} # add values to this table using self.routing_table[dest] = Table()
        self.lsp = {} # add values to this table using self.lsp[src] = LinkStatePacket()


    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            if packet.dstAddr == self.addr:
                pass
            elif packet.dstAddr in list(self.routing_table.keys()):
                self.send(self.routing_table[packet.dstAddr].next_hop, packet)
        else:
            # check the sequence number
            sqno, links = self.objectifyContent(packet.content)
            # print ("Objectify:", self.addr, len(links))
            # if the sequence number is higher and the received link state is different
            if packet.srcAddr not in list(self.lsp.keys()) or sqno > self.lsp[packet.srcAddr].seq_no:
                # print ("Received: New LSP", packet.srcAddr)
                #   update the local copy of the link state
                self.lsp[packet.srcAddr] = LinkStatePacket(packet.srcAddr, sqno, links)
                #   update the forwarding table
                self.updateRoutingTable()
                #   broadcast the packet to other neighbors
                self.forwardState(packet, port)

    


    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        str_content = self.stringifyContent(self.links, self.sq_nb)
        _, links = self.objectifyContent(str_content)
        # update the forwarding table
        self.lsp[self.addr] = LinkStatePacket(self.addr, self.sq_nb, links)
        self.updateRoutingTable()
        # broadcast the new link state of this router to all neighbors
        self.broadcastState()



    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        str_content = self.stringifyContent(self.links, self.sq_nb)
        _, links = self.objectifyContent(str_content)
        # update the forwarding table
        self.lsp[self.addr] = LinkStatePacket(self.addr, self.sq_nb, links)
        self.updateRoutingTable()
        # broadcast the new link state of this router to all neighbors
        self.broadcastState()


    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            self.broadcastState()


    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return ""

    def findEgress(self, egress_router):
        """Find the egress port corrresponding to a router"""
        for port in list(self.links.keys()):
            if (self.links[port].e1 == self.addr and self.links[port].e2 == egress_router) \
                or (self.links[port].e2 == self.addr and self.links[port].e1 == egress_router):
                return port


    def stringifyContent(self, links, sqno):
        """Convert link information to a string to broadcast over the newtwork"""
        link_string = str(sqno) + " : "
        for port in list(links.keys()):
            endpoint1 = str(links[port].e1)
            endpoint2 = str(links[port].e2)
            cost = str(links[port].l12)
            link_string += endpoint1 + "," + endpoint2 + "," + cost + " : "
        return link_string
    
    def objectifyContent(self, link_string):
        """Convert the recieved link information into Link object"""
        link_list = []
        links = link_string.split(" : ")
        sqno = int(links[0])
        for link in links[1:]:
            pieces = link.split(",")
            if len(pieces) == 3:
                link_list.append(Link(pieces[0], pieces[1], int(pieces[2]), int(pieces[2]), 1))
        return sqno, link_list

    def updateRoutingTable(self):
        """Update the routing table using the link state received from different nodes"""
        # self.printLSP()
        # Initialize a graph and add weighted edges
        graph = nx.Graph()
        for router in list(self.lsp.keys()):
            for link in self.lsp[router].neighbors:
                graph.add_weighted_edges_from([(link.e1, link.e2, link.l12)])

        # for all nodes in graph, find the path and add to routing table
        for node in graph.nodes():
            if node != self.addr:
                try:
                    path = nx.dijkstra_path(graph, self.addr, node)
                    egress_port = self.findEgress(path[1])
                    # print ("Path:", path, "Router:", path[1], "1st Hop:", egress_port)
                    self.routing_table[node] = Table(node, 1, egress_port)
                except nx.NetworkXNoPath:
                    print ("path doesn't exist")
        # self.printTable()
    
    def printLSP(self):
        """Print the Link States of the network"""
        print ("LSP", self.addr)
        for node in list(self.lsp.keys()):
            print (self.lsp[node].src_router, self.lsp[node].seq_no, len(self.lsp[node].neighbors))
    
    def printTable(self):
        """Print routing table of a router"""
        print ("Routing Table", self.addr)
        for node in list(self.routing_table.keys()):
            print(self.routing_table[node].destination, self.routing_table[node].next_hop)

    def broadcastState(self):
        """Broadcast links info to the neighboring routers"""
        self.sq_nb = self.sq_nb + 1
        content = self.stringifyContent(self.links, self.sq_nb)
        # print ("Broadcast:", self.addr, content)
        for port in list(self.links.keys()):
            pkt = None
            if self.links[port].e1 == self.addr:
                pkt = Packet(2, self.addr, self.links[port].e2, content)
            elif self.links[port].e2 == self.addr:
                pkt = Packet(2, self.addr, self.links[port].e1, content)
            self.send(port, pkt)

    def forwardState(self, packet, ingress_port):
        """Forward the received link state to the neighboring routers except the one that sent it out"""
        for port in list(self.links.keys()):
            pkt = None
            if port != ingress_port:
                if self.links[port].e1 == self.addr:
                    pkt = Packet(2, packet.srcAddr, self.links[port].e2, packet.content)
                elif self.links[port].e2 == self.addr:
                    pkt = Packet(2, packet.srcAddr, self.links[port].e1, packet.content)
            self.send(port, packet)
