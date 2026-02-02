import math
from threading import Thread, Condition
import time
from nodeServer import NodeServer
from nodeSend import NodeSend
from message import Message, MESSAGE_RELEASE, MESSAGE_REPLY, MESSAGE_REQUEST
import config
import random


class Node(Thread):
    _FINISHED_NODES = 0
    _HAVE_ALL_FINISHED = Condition()

    def __init__(self, id):
        Thread.__init__(self)
        self.id = id
        self.port = config.port + id
        self.daemon = True
        self.lamport_ts = 0

        self.replying_to = None
        self.replying_ts = None
        self.my_request_ts = None
        self.nodes_to_reply = []

        
        self.replies = set()
        self.replies_lock = Condition()
        self.in_cs = False
        self.state_lock = Condition()

        collegues_set = set() # para evitar repeticiones 

        k = math.ceil(math.sqrt(config.numNodes))
        row = self.id // k
        col = self.id % k

        for c in range(k):
            node = row * k + c
            if node < config.numNodes:
                collegues_set.add(node)
            
        for r in range(k):
            node = r * k + col
            if node < config.numNodes:
                collegues_set.add(node)

        self.collegues = list(collegues_set)

        self.server = NodeServer(self)
        self.server.start()

        self.client = NodeSend(self)

    def do_connections(self):
        self.client.build_connection()

    def run(self):
  

        print("Run Node%i with the follows %s"%(self.id,self.collegues))
        self.client.start()

        self.wakeupcounter = 0
        while self.wakeupcounter <= 2: # criterio de parada: 3 peticiones por nodo
            # Nodes with different starting times
            time.sleep(random.randint(2, 5))
            print(f"Node_{self.id} attempting access (Attempt {self.wakeupcounter})")

            acces_acquired = False

            while not acces_acquired:
                acces_acquired = self.request_access() # vuelve a intentario
                if not acces_acquired:
                    time.sleep(random.uniform(1.0, 3.0)) # espera un tiempo antes de reintentar

            # entra en la cs
            print(f"Node_{self.id} entered in critical section...")

            work_time = 1
            time.sleep(work_time)  # Simula trabajo en la sección crítica

            print(f"Node_{self.id} releasing access...")
            self.release_access()

            self.wakeupcounter += 1

        # Wait for all nodes to finish
        print("Node_%i is waiting for all nodes to finish"%self.id)
        self._finished()

        print("Node_%i DONE!"%self.id)

    def request_access(self):
        
        with self.replies_lock:
            self.replies = set()

        with self.state_lock:
            self.lamport_ts += 1
            self.my_request_ts = self.lamport_ts

        print(f"Node_{self.id} is requesting access to CS at time {self.lamport_ts}")

        # Multicast Request
        for entity in self.collegues:
            msg = Message(MESSAGE_REQUEST, self.id, entity, self.my_request_ts, "Req")
            self.client.send_message(msg, entity)

        # Timeout
        timeout = 10.0
        start = time.time()

        # Check votes received for accessing CS
        with self.replies_lock:
            while len(self.replies) < len(self.collegues):
                remaining = timeout - (time.time() - start)
                if remaining <= 0:
                    print(f"Node_{self.id} timeout while requesting access to CS")
                    self.release_access(partial_failure=True)
                    return False

                self.replies_lock.wait(timeout=remaining)

        self.in_cs = True
        return True

    def release_access(self, partial_failure=False):
        """
        Release access to critical section
        :param timeout: If True, indicates that the release is due to a timeout
        """
        if not partial_failure:
            with self.state_lock:
                self.in_cs = False
                self.my_request_ts = None

        # Enviar release a todos los nodos en self.collegues
        msg = Message(msg_type=MESSAGE_RELEASE, src=self.id, data="Rel")
        self.client.multicast(msg, self.collegues)

        with self.replies_lock:
            self.replies.clear()

    def _finished(self):
        with Node._HAVE_ALL_FINISHED:
            Node._FINISHED_NODES += 1
            if Node._FINISHED_NODES == config.numNodes:
                Node._HAVE_ALL_FINISHED.notify_all()

            while Node._FINISHED_NODES < config.numNodes:
                Node._HAVE_ALL_FINISHED.wait()