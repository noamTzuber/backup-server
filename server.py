# Noam Tzuberi 313374837 and Itay Shwartz 318528171

import socket
import sys
import string
import random
import os
import time
from utils import *

garbage_list = []
computer_number = 1
delete_list = []
empty_id = '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'

# ===============================================================================
# random_string - this function create random string in length 128 that contains letters and numbers.
#
# return the random string
# ===============================================================================
def random_string():
    character_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(character_set) for i in range(128))


# ===============================================================================
# registered_new_id - the function register a new user that connect without id, and upload his new directory.
# the function add new user to the dict
#
# client_socket - the socket of th client
# dict - contains all the data about the users
# ===============================================================================
def registered_new_id(client_socket, dict):
    global computer_number
    # we make random string that will be the id of the user
    id = random_string()
    print(id)
    try:
        # we make directory to all the files that the user will upload
        os.makedirs(id)

        # add the new user to the dict
        dict_id = {}
        dict_id[computer_number] = list()
        dict[id] = dict_id

        # send to the user his new id and cp_num (to one user can be more than one cp_num)
        client_socket.send(id.encode("utf-8") + computer_number.to_bytes(4, "big"))
        computer_number += 1
    except:
        pass
    # absolute_path = id
    path = id
    # upload the user directory to the server
    pull(client_socket, path, garbage_list)


# ===============================================================================
# register_new_cp - this function add on more user (another cp) to the exist id, send to the client the id
# and the new cp_num. finally push to the new user all the data in the server about the id to him.
#
# id - the id of the client - in the dict already
# client_socket -  the socket of the client
# dict - contains all the data about the users
# ===============================================================================
def register_new_cp(id, client_socket, dict):
    global computer_number
    # add the cp_num to the dict of the id
    dict[id][computer_number] = list()
    client_socket.send(id.encode("utf-8") + computer_number.to_bytes(4, "big"))
    computer_number += 1
    # send all the file to the client
    push(client_socket, id)


# ===============================================================================
# update_dict - this function get list of command from specific cp_num and update all the cp's that relevant
#
# id - the id of the client
# cp_num - the computer number of the client
# ===============================================================================
def update_dict(id, cp_num, list, dict):
    client_dict = dict[id]
    for cp in client_dict:
        if cp != cp_num:
            client_dict[cp].extend(list)


# ===============================================================================
# received_list - this function create update list from the client
#
# socket - the socket of the client
# the function return the command_list
# ===============================================================================
def received_list(socket):
    # create empty list
    command_list = []
    while True:
        # get the size of the command that we add to the list
        command_size = int.from_bytes(socket.recv(4), "big")

        if command_size == 0:
            break

        # received the command
        command = socket.recv(command_size).decode(errors='ignore')
        command_list.append(command)
    # return the command_list
    return command_list



def avoid_delete_cycles(updates_list, id, cp_num):
    try:
        global delete_list
        global dict
        i = 0
        while i < len(updates_list):
            if updates_list[i][:1] == 'd':
                delete_list.append(updates_list[i])
            elif updates_list[i][:1] == 'c' or  updates_list[i][:1] == 'z':
                check_size = len(dict[id])*2 - 1
                for command in reversed(delete_list):
                    check_size = check_size - 1
                    if command[2:] != updates_list[i][2:]:
                        break
                    if check_size == 0:
                        updates_list.pop(i)
                        dict[id][cp_num].append(command)
            i = i + 1
    except:
        pass






# ===============================================================================
# receive_update_from_client - this function received update from client
#
# id - the id of the client - in the dict already
# cp_num - the computer number of the client
# client_socket -  the socket of the client
# dict - contains all the data about the users
# ===============================================================================
def receive_update_from_client(id, cp_num, dict, client_socket):
    garbage_list = []

    # create update list from client
    updates_list = received_list(client_socket)

    avoid_delete_cycles(updates_list, id, cp_num)

    # update the dict with new commands
    update_dict(id, cp_num, updates_list, dict)

    # received data from the client
    pull(client_socket, id, garbage_list)


# ===============================================================================
# main - this function is the main function of the server. the server is always on. the server can handle
# appeals of client - registers, send new updates and received update from client
#
# ===============================================================================
if __name__ == '__main__':
    # create new socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(sys.argv[1])))
    # the server can
    server.listen(5)
    # create new dictionary that contains the data about all the users (id, cp, updates to do)
    dict = {}

    while True:
        client_socket, client_address = server.accept()

        # received new appeal from client - fix size of id and cp_num - 132
        data = client_socket.recv(132)
        id = data[:128].decode()
        cp_num = int.from_bytes(data[128:], "big")

        # if the client don't have id and cp_num - we sign him and upload his file
        if id == empty_id:
            registered_new_id(client_socket, dict)
        # if the client don't have cp_num - we sign the client and push to the client all id file
        elif cp_num == 0:
            register_new_cp(id, client_socket, dict)
        # we know the client - so we send to him updates that accrued, and get from the client his changes.
        else:
            send_update(dict[id][cp_num], client_socket, id)
            receive_update_from_client(id, cp_num, dict, client_socket)

        # wen we finished with the client we close his socket - to make room for another clients to appeal
        client_socket.close()
