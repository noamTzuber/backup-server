# Noam Tzuberi 313374837 and Itay Shwartz 318528171

import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from utils import *

ID = '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
CP_NUM = 0
my_observer = None
empty_id = '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
SEPARATOR = "<SEPARATOR>"
updates_list = []
black_list = []


# ===============================================================================
# open_socket - the func open new socket to connect with the server. each time
# new connect for let the server talk with others clients.
#
# the func return the socket to the client
# ===============================================================================
def open_socket():
    # open the socket with TCP protocol
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # the socket connect to the server
    s.connect((sys.argv[1], int(sys.argv[2])))
    return s


# ===============================================================================
# register - the func register new pc to the server for get updates . if the ID exist
# the computer get the a cp number , else the computer get the an ID and cp number.
# if there was ID the func pull all the folder from the server
# if there wasn't ID the func push all the folder of the user to the server
# ===============================================================================
def register():
    global ID
    global CP_NUM
    global empty_id
    global black_list

    # flag - if to push the folder user to the server
    to_push = 0

    # if the ID exist
    if ID == empty_id:
        # change the flag to push the folder to the server
        to_push = 1

    # open new socket
    s = open_socket()

    # send the socket and the cp number
    s.send(ID.encode() + CP_NUM.to_bytes(4, "big"))

    # get the ID and CP number from server
    identity = s.recv(132)

    # decode them
    ID = identity[:128].decode("utf-8")
    CP_NUM = int.from_bytes(identity[128:132], "big")

    # if need to push folder to rhe server or pull the server folder
    if to_push:
        push(s, sys.argv[3])
    else:
        pull(s, sys.argv[3], black_list)
    # close the socket
    s.close()


# ===============================================================================
# on_created - watchdog func "jump" when the client create dir/file in his folder
# checking if the creating was dir or file  and added it to the list we need send to server
# but, if the command done because another client we done need to save this action in the list
#
# event - object that contain the path of the  dir/file change
# ===============================================================================
def on_created(event):
    global updates_list
    global black_list
    # isolate the path of the event
    local_path = event.src_path.replace(sys.argv[3], '')[1:]

    # checking if it dir or file
    is_dir = "cf"
    if event.is_directory:
        is_dir = "cd"

    # if the command got from another client return
    if shrink_list(is_dir + local_path, black_list):
        return
    # add the command to list that will send to server
    updates_list.append(is_dir + local_path)


# ===============================================================================
# on_deleted - watchdog func "jump" when the client delete dir/file in his folder
# and add the list the command to delete the wanted object
#
# event - object that contain the path of the  dir/file change
# ===============================================================================
def on_deleted(event):
    global updates_list

    # isolate the path of the event
    local_path = event.src_path.replace(sys.argv[3], '')[1:]

    # add the command to list that will send to server
    updates_list.append("dd" + local_path)


# ===============================================================================
# on_moved -  watchdog func "jump" when the client rename dir/file in his folder
# the func create the command and add it to the list
#
# event - object that contain the path of the  dir/file change
# ===============================================================================
def on_moved(event):
    global updates_list
    # isolate the src name- the name before the change
    src_path = event.src_path.replace(sys.argv[3], '')[1:]

    # isolate the dst name- the name after the change
    dst_path = event.dest_path.replace(sys.argv[3], '')[1:]

    # checking if dir or file
    is_dir = "mf"
    if event.is_directory:
        is_dir = "md"

    # add the command to list that will send to server
    updates_list.append(is_dir + src_path + SEPARATOR + dst_path)


# ===============================================================================
# on_modified -  watchdog func "jump" when the client rename dir/file in his folder
# the func check if the modify was in file because if it dir the change was in the files iside
# or deleted dirs or creating - another function will care them. add the command to the list
#
# event - object that contain the path of the  dir/file change
# ===============================================================================
def on_modified(event):
    global updates_list
    modify = 'zf'

    # check if the modify was in dir
    if event.is_directory is False:
        # isolate the path of the event
        local_path = event.src_path.replace(sys.argv[3], '')[1:]

        # add to the list
        updates_list.append(modify + local_path)


# ===============================================================================
# create_observer - creating the observer for the watch dog
# the observer will warn about the changes
#
# path - the path that the observer will warn if the change was in this folder
# the func return the object of the observer
# ===============================================================================
def create_observer(path):
    global my_observer

    # the changes that the observer warn
    my_event_handler = PatternMatchingEventHandler(["*"], None, False, True)

    # the function that the observer will do for changes
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_modified = on_modified
    my_event_handler.on_moved = on_moved

    # observer constructor
    my_observer = Observer()
    my_observer.schedule(my_event_handler, path, recursive=True)

    return my_observer


# ===============================================================================
# send_identity - the func send the ID and the cp num to the server
#
# s -the socket to connect the server
# ===============================================================================
def send_identity(s):
    global ID
    global CP_NUM

    # send the ID and cp number
    s.send(ID.encode() + CP_NUM.to_bytes(4, "big"))


# ===============================================================================
# send_list - the func send the list to the server. the list content the changes that done
#
# s -the socket to connect the server
# ===============================================================================

def send_list(s):
    global updates_list
    shrink_modifies(update_list)
    shrink_commands(updates_list)
    shrink_deletes(updates_list)
    empty_list = 0
    # move all the command in list
    for command in updates_list:
        # the length of the command
        s.send((len(command.encode())).to_bytes(4, "big"))

        # the command itself
        s.send(command.encode())

    # the list is empty
    s.send(empty_list.to_bytes(4, "big"))


# ===============================================================================
# main - check if the client has ID - if not give it one and pull his folder to server.
# if he have , the client create a folder that the server will push all his folder to this folder
# after that the client will connect to server each period time(given in the arguments)
# look for changes from server and give updates to the server
#
# ===============================================================================
if __name__ == '__main__':
    # if there is  ID will create dir in the client cp - for saving the server folder
    try:
        ID = sys.argv[5]
        os.mkdir(sys.argv[3])
    except:
        pass

    # create the observer
    my_observer = create_observer(sys.argv[3])

    # start the observer
    my_observer.start()

    # register the client
    register()

    try:
        # appeal to the server for limited time
        while True:

            # the time that the client need to wait
            time.sleep(int(sys.argv[4]))

            # creating new connection to the server pull changes and send updates
            s = open_socket()
            send_identity(s)
            pull(s, sys.argv[3], black_list)
            send_list(s)
            send_update(updates_list, s, sys.argv[3])

            # close the connection to the server
            s.close()
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()
