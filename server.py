import math
import socket
import threading
import pickle
import random
import numpy

# socket connection data
HEADER = 4096
FORMAT = "utf-8"
SERVER = socket.gethostbyname(socket.gethostname())  # local IP
PORT = 8080
ADDR = (SERVER, PORT)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

# list of all players
list_of_players = {}

# randomly generate number of players to check out working
for i in range(1, 1000):
    lat = round(numpy.random.uniform(-90, 90), 6)
    long = round(numpy.random.uniform(-180, 180), 6)
    list_of_players[i] = {"role": "runner", "name": f"{i}", "cord": [round(lat, 6), round(long, 6)]}

for i in range(1001, 2000):
    lat = round(numpy.random.uniform(-90, 90), 6)
    long = round(numpy.random.uniform(-180, 180), 6)
    list_of_players[i] = {"role": "catcher", "name": f"{i}", "cord": [round(lat, 6), round(long, 6)]}


# handle all of data transmission with one player
def handle_client(conn):
    connected = True
    personal_id = random.randint(1, 1000000)
    role = random.randint(0, 10)
    if role < 8:
        player_role = "runner"
    else:
        player_role = "catcher"

    while connected:
        try:
            pass_msg = conn.recv(HEADER)
            unpacked_pass = pickle.loads(pass_msg)
            if unpacked_pass == "start":
                starting_data = pickle.dumps([personal_id, player_role])
                conn.send(starting_data)
                starting_cords = conn.recv(HEADER)
                unpacked_starting_cord = pickle.loads(starting_cords)
                list_of_players[personal_id] = {"role": player_role,
                                                "name": None,
                                                "cord": [unpacked_starting_cord[0], unpacked_starting_cord[1]]}
            elif unpacked_pass == "cord":
                cords = conn.recv(HEADER)
                unpacked_cords = pickle.loads(cords)
                list_of_players[personal_id]["name"] = unpacked_cords["name"]
                list_of_players[personal_id]["cord"] = unpacked_cords["cord"]
                if list_of_players[personal_id]["role"] == "catcher":
                    final_list = {}
                    for key, value in list_of_players.items():
                        if key in find_closest(personal_id):
                            final_list[key] = value
                    list_to_send = [list_of_players[personal_id], final_list]
                    packed_list = pickle.dumps(list_to_send)
                    conn.send(packed_list)
                elif list_of_players[personal_id]["role"] == "runner":
                    final_list = {}
                    for key, value in list_of_players.items():
                        if key in find_closest(personal_id)[:1]:
                            final_list[key] = value
                    list_to_send = [list_of_players[personal_id], final_list]
                    packed_list = pickle.dumps(list_to_send)
                    conn.send(packed_list)
            elif unpacked_pass == "catch":
                pair = conn.recv(HEADER)
                to_check = pickle.loads(pair)
                if check_distance(to_check[0], to_check[1]):
                    status = True
                    packed_status = pickle.dumps(status)
                    conn.send(packed_status)
                else:
                    status = False
                    packed_status = pickle.dumps(status)
                    conn.send(packed_status)
        except ConnectionResetError:
            conn.close()
            list_of_players.pop(personal_id)
            connected = False


# init connection
def start():
    server.listen()
    print(f"server is listening {SERVER}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


# it is checking distance between two players and if there close enough it is reversing their roles and returning True
def check_distance(player1, player2):
    dif_one = abs(list_of_players[player1]["cord"][0] - list_of_players[player2]["cord"][0])
    dif_two = abs(list_of_players[player1]["cord"][1] - list_of_players[player2]["cord"][1])
    distance = math.sqrt(dif_two * dif_two + dif_one * dif_one)
    if distance <= 0.00015:
        if list_of_players[player1]["role"] == "runner":
            list_of_players[player1]["role"] = "catcher"
            list_of_players[player2]["role"] = "runner"
        elif list_of_players[player1]["role"] == "catcher":
            list_of_players[player1]["role"] = "runner"
            list_of_players[player2]["role"] = "catcher"
        return True


# it is sorting list of players by a distance to the given player and returning 50 closest
def find_closest(player):
    closest = {}
    for player2 in list_of_players:
        if list_of_players[player2]["role"] != list_of_players[player]["role"]:
            dif_one = abs(list_of_players[player]["cord"][0] - list_of_players[player2]["cord"][0])
            dif_two = abs(list_of_players[player]["cord"][1] - list_of_players[player2]["cord"][1])
            distance = math.sqrt(dif_two * dif_two + dif_one * dif_one)
            closest[player2] = distance
    sort_closest = sorted(closest.items(), key=lambda x: x[1], reverse=False)
    keys = [key for key, value in sort_closest]
    return keys[:50]


start()
