import select
from threading import Thread
import utils
from message import Message, MESSAGE_REQUEST, MESSAGE_RELEASE, MESSAGE_REPLY
import json
import heapq


class NodeServer(Thread):
    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
        self.daemon = True

    def run(self):
        self.update()

    def update(self):
        self.connection_list = []
        self.server_socket = utils.create_server_socket(self.node.port)
        self.connection_list.append(self.server_socket)

        while self.node.daemon:
            (read_sockets, write_sockets, error_sockets) = select.select(
                self.connection_list, [], [], 5)
            if not (read_sockets or write_sockets or error_sockets):
                continue

            else:
                for read_socket in read_sockets:
                    if read_socket == self.server_socket:
                        (conn, addr) = read_socket.accept()
                        self.connection_list.append(conn)
                    else:
                        try:
                            data = read_socket.recv(4096)
                            # Had to add spliter for messages to prevent errors
                            str_data = data.decode("utf-8")
                            for part in str_data.split('}'):
                                if '{' in part:
                                    try:
                                        ms_dict = json.loads(part + '}')
                                        msg = Message(
                                            msg_type=ms_dict.get('msg_type'),
                                            src=ms_dict.get('src'),
                                            dest=ms_dict.get('dest'),
                                            ts=ms_dict.get('ts'),
                                            data=ms_dict.get('data')
                                        )
                                        self.process_message(msg)
                                    except:
                                        pass
                        except:
                            if read_socket in self.connection_list:
                                self.connection_list.remove(read_socket)
                            read_socket.close()
                            continue

        self.server_socket.close()

    def process_message(self, msg):
        with self.node.state_lock:
            if msg.ts:
                self.node.lamport_ts = max(self.node.lamport_ts, msg.ts) + 1

        if msg.msg_type == MESSAGE_REQUEST:
            self.handle_request(msg)
        elif msg.msg_type == MESSAGE_REPLY:
            self.handle_reply(msg)
        elif msg.msg_type == MESSAGE_RELEASE:
            self.handle_release(msg)

    def handle_request(self, msg):
        with self.node.state_lock:
            # If no one has requested yet, grant it
            if self.node.replying_to is None:
                self.node.replying_to = msg.src
                self.node.replying_ts = msg.ts
                reply = Message(msg_type=MESSAGE_REPLY, src=self.node.id, dest=msg.src, data="Vote")
                self.node.client.send_message(reply, msg.src)
                print(f"Node_{self.node.id}: Granted to Node_{msg.src}")
            else:
                # Heap for priority queue
                heapq.heappush(self.node.nodes_to_reply, (msg.ts, msg.src))
                print(f"Node_{self.node.id}: Busy with Node_{self.node.replying_to}, queued Node_{msg.src}")

    def handle_reply(self, msg):
        # Release waiting condition locks
        with self.node.replies_lock:
            self.node.replies.add(msg.src)
            self.node.replies_lock.notify_all()

    def handle_release(self, msg):
        with self.node.state_lock:
            # Check if the node that released the lock is the one that is granted
            if self.node.replying_to == msg.src:
                self.node.replying_to = None
                self.node.replying_ts = None

                if self.node.nodes_to_reply:
                    (next_ts, next_tsnode) = heapq.heappop(self.node.nodes_to_reply)
                    self.node.replying_ts = next_ts
                    self.node.replying_to = next_node
                    self._send_reply(next_node) # enviar reply al siguiente nodo en la cola
                    print(f"Node_{self.node.id}: Granted to Node_{node} from queue")
            else:
                # Elimina todos los nodos que estaban respondiendo al nodo que se ha liberado en caso de error o timeout
                self.node.nodes_to_reply = [x for x in self.node.nodes_to_reply if x[1] != msg.src]
                heapq.heapify(self.node.nodes_to_reply)
def _send_reply(self, dest):
        reply = Message(msg_type=MESSAGE_REPLY, src=self.node.id, dest=dest, data="Vote")
        self.node.client.send_message(reply, dest)