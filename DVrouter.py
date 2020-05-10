import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads

class Table:
    """Forwarding Table Entry"""
    def __init__(self, _cost, _next_hop, _port):
        self.cost = _cost
        self.next_hop = _next_hop
        self.port = _port

class DistVector:
    """Vector to broadcast"""
    def __init__(self, _router, _cost, _next):
        self.src_router = _router
        self.cost = _cost
        self.next_hop = _next

class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        self.fwd_table = {} # add values to this table using self.routing_table[dest] = Table()
        self.dv = {} # add values to this table using self.dv[src] = DistanceVector()

    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            if packet.dstAddr == self.addr:
                pass
            elif packet.dstAddr in list(self.fwd_table.keys()):
                self.send(self.fwd_table[packet.dstAddr].port, packet) 
        else:
            dist_vector = self.objectifyContent(packet.content)
            if packet.srcAddr not in list(self.dv.keys()) \
                or not self.isEqualDistVector(dist_vector, self.dv[packet.srcAddr]):
                    self.dv[packet.srcAddr] = dist_vector
                    self.updateRoutingTable(packet.srcAddr)
                    self.broadcastState()
                    # self.printTable()

    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # update the distance vector of this router
        # self.dv[self.addr].append(DistVector(endpoint, cost, endpoint)) 
        self.fwd_table[endpoint] = Table(cost, endpoint, port)
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors
        self.broadcastState()
        
    def isEqualDistVector(self, v1, v2):
        if len(v1.keys()) != len(v2.keys()):
            return False
        for dest in list(v1.keys()):
            if v1[dest].cost != v2[dest].cost \
                or v1[dest].src_router != v2[dest].src_router \
                    or v1[dest].next_hop != v2[dest].next_hop:
                    return False
        return True


    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors
        pass


    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # broadcast the distance vector of this router to neighbors
            pass


    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return ""

    def findEgress(self, egress_router):
        """Find the egress port corrresponding to a router"""
        for port in list(self.links.keys()):
            if (self.links[port].e1 == self.addr and self.links[port].e2 == egress_router) \
                or (self.links[port].e2 == self.addr and self.links[port].e1 == egress_router):
                return port
    
    def stringifyContent(self):
        """Convert routing vector information to a string to broadcast over the newtwork"""
        vector_string = ""
        for dst in self.fwd_table.keys():
            cost = str(self.fwd_table[dst].cost)
            hop = str(self.fwd_table[dst].next_hop)
            vector_string += dst + "," + cost + "," + hop + " : "
        return vector_string
    
    def objectifyContent(self, vector_string):
        """Convert the recieved routing vector information into Link object"""
        dist_vector = {}
        vectors = vector_string.split(" : ")
        for entry in vectors:
            pieces = entry.split(",")
            if len(pieces) == 3:
                dist_vector[pieces[0]] = DistVector(pieces[0], int(pieces[1]), pieces[2])
        return dist_vector

    def broadcastState(self):
        """Broadcast links info just to the neighboring routers"""
        content = self.stringifyContent()
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
    
    def updateRoutingTable(self, src):
        for dest in list(self.dv[src].keys()):
            if dest not in list(self.fwd_table.keys()) \
                or self.dv[src][dest].cost + 1 < self.fwd_table[dest].cost:
                cost = self.dv[src][dest].cost + self.fwd_table[src].cost
                port = self.findEgress(src)
                self.fwd_table[dest] = Table(cost, src, port)

    def printTable(self):
        """Print routing table of a router"""
        print ("Routing Table", self.addr)
        for node in list(self.fwd_table.keys()):
            print(node, self.fwd_table[node].next_hop, self.fwd_table[node].cost)
