# Noam Tzuberi 313374837 and Itay Shwartz 318528171

import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SEPARATOR = "<SEPARATOR>"
counter = 1
BUFFER_SIZE = 50000


def shrink_commands(updates_list):
    try:
        # index for command that not create modify and move
        i = 0
        while i < (len(updates_list)):
            # if to increase i
            inc_i = 1
            # index for command "delete"
            j = i
            # for all the commands after the current i command
            while j < (len(updates_list)):
                # if the command not delete
                if updates_list[i][:1] != "d":
                    # check if there is delete in the rest of the list
                    if updates_list[i][2:] == updates_list[j][2:] and updates_list[j][:1] == 'd':
                        # pop the current command
                        updates_list.pop(i)
                        # don't increase i
                        inc_i = 0
                        # don't increase i
                        j = j - 1
                # increase j every loop
                j = j + 1
            # increase i if we didn't fount match
            if inc_i:
                i = i + 1
    except:
        pass


# ===============================================================================
# shrink_list - this function shrink the list - if command from some update appear in the black list - so
# is mean that the watch dog jump about action that the sender told him to to - so we prevent sending back the data,
# return 1 and pop the command from the black list
#
# command- command that we need to check if appear in the black list.
# black_list - list of commands that the sender told us to do
# ===============================================================================
def shrink_list(command, black_list):
    for i in range(len(black_list)):
        if command == black_list[i]:
            black_list.pop(i)
            return 1


def shrink_deletes(updates_list):
    try:
        i = 0
        while i < (len(updates_list)):
            if updates_list[i][:1] == "d":
                if updates_list[i] == updates_list[i + 1]:
                    updates_list.pop(i)
                    i = i - 1
            i = i + 1
    except:
        pass


def shrink_modifies(updates_list):
    try:
        i = 0
        while i < (len(updates_list)):
            if updates_list[i][:1] == "z":
                if updates_list[i] == updates_list[i + 1]:
                    updates_list.pop(i)
                    i = i - 1
            i = i + 1
    except:
        pass


# ===============================================================================
# push - this function send all the files and directories from a given path to receiver on given socket
#
# socket - socket to send
# path - path from the disk
# ===============================================================================
def push(socket, path):
    done = 0
    # we go throws all the file
    for root, dirs, files in os.walk(path, topdown=True):
        # for files
        for name in files:
            # the command that we sent it 'cf' (create file) + the path
            command = "cf" + (os.path.join(root, name).replace(path, ''))[1:]
            current_path = os.path.join(path, command[2:])
            # send the length of the command, and next the command
            socket.send((len(command.encode()).to_bytes(4, "big")))
            socket.send(command.encode())
            # ofter we send the file itself
            send_file(command, current_path, socket)
        # for directories
        for name in dirs:
            # the command that we sent it 'cd' (create dir)
            command = "cd" + os.path.join(root.replace(path, '')[1:], name)
            send_dir(command, socket)
    # when we finish go throws the file - we send done (0)
    socket.send(done.to_bytes(4, "big"))


# src_path - the absolute path (example sys.argv[3] or id)
# ===============================================================================
# pull - this function get from sender new updates
#
# socket - socket to send
# src_path - path from the disk
# black_list - list of commands thad the sender told us to do
# ===============================================================================
def pull(socket, src_path, black_list):
    # we receive commands until we receive size == 0
    while True:
        size = socket.recv(4)
        size = int.from_bytes(size, "big")
        if size == 0:
            break

        # we get new command, and take the action, is dir and local_path from it.
        command = (socket.recv(size)).decode(errors='ignore')
        action = command[:1]
        is_dir = command[1:2]
        local_path = command[2:]

        # create the full path from src_path and local_path
        full_path = os.path.join(src_path, local_path)

        # we go the the correct function according to the command that we received
        if action == "c":
            # we add to the black list only the command of creation - those are the problematic
            black_list.append(command)
            if is_dir == "d":
                receive_dir(full_path)
            else:
                receive_file(full_path, socket)

        elif action == "d":
            if os.path.isdir(full_path):
                delete_dirs(full_path)
            else:
                delete_file(full_path)
        # z mean modify
        elif action == "z":
            receive_modify(full_path, socket)

        elif action == "m":
            move_dir_file(src_path, local_path)


# ===============================================================================
# send_file - this function send file from sender to receiver
#
# path - the path of the file
# socket - to send data
# ===============================================================================
def send_file(command, path, socket):
    # first, if the receiver tell us that the file already exist on his computer - we return. else - we send
    is_exist = socket.recv(4)
    is_exist = int.from_bytes(is_exist, "big")
    if is_exist:
        return

    # we try to get the size if the file
    try:
        size_of_file = os.path.getsize(path)
    except:
        # if we cant get hime - we send that the size is 0 and return
        socket.send((0).to_bytes(4, "big"))
        return

    # else - we send the size of file
    socket.send(size_of_file.to_bytes(4, "big"))

    try:
        # send the file
        with open(path, "rb") as f:
            while True:
                # read the bytes from the file
                bytes_read = f.read(BUFFER_SIZE)

                if not bytes_read:
                    f.close()
                    break

                socket.send(bytes_read)
    except:
        pass


# ===============================================================================
# receive_file - this function received file from sender, and create it
#
# path - the path of the file
# socket - to send data
# ===============================================================================
def receive_file(path, socket):
    # send to the server if the file exist in our computer or not (1 or 0). if not exist - go out.
    if os.path.exists(path):
        socket.send((1).to_bytes(4, "big"))
        return
    socket.send((0).to_bytes(4, "big"))

    # get the size of the file that we get
    size_bytes = socket.recv(4)
    file_size = int.from_bytes(size_bytes, "big")

    first_read = 1
    try:
        # open new file on the path as f
        with open(path, "wb") as f:
            while True:
                # received bytes from the sender - BUFFER_SIZE or file_size
                bytes_read = socket.recv(min(BUFFER_SIZE, file_size))

                # if it the first read, and we dont get any bytes, we truncate the file, close it and break
                if first_read and not bytes_read:
                    f.truncate(0)
                    f.close()
                    break

                # write the bytes
                f.write(bytes_read)
                first_read = 0

                # update the new file size - the amount of bytes that we need to receive until we finish
                file_size = file_size - len(bytes_read)
                # if there is no bytes to received - close and break
                if file_size == 0:
                    f.close()
                    break
    # if problem had accrue when we receiving, we continue to received the amount of bytes that the server sent - that
    # how we keep the synchronize of the sender-receiver
    except:
        while True:
            bytes_read = socket.recv(min(BUFFER_SIZE, file_size))
            file_size = file_size - len(bytes_read)
            if file_size == 0:
                f.close()
                break


# ===============================================================================
# send_dir - send command to create dir
#
# command - the command of the dir that will create
# socket - the connection to the receiver
# ===============================================================================
def send_dir(command, socket):
    # encode the commands
    socket.send((len(command.encode())).to_bytes(4, "big"))
    socket.send(command.encode("utf-8"))


# ===============================================================================
# receive_dir -  create dir
#
# path - the path of the dir that will create
# ===============================================================================
def receive_dir(path):
    try:
        # try to create dir - if not exist
        os.mkdir(path)
    except:
        pass


# ===============================================================================
# delete_dirs - move all the dirs and file below the dir we want to delete by using
# recursion
#
# path - the path of the dir that will delete
# ===============================================================================
def delete_dirs(path):
    # pass all the objects below the wanted dir
    for root, dirs, files in os.walk(path, topdown=False):

        # delete all the files if exist
        for name in files:
            if os.path.exists(os.path.join(root, name)):
                os.remove(os.path.join(root, name))

        # delete root dir if exist
        if os.path.exists(root):
            os.rmdir(root)



# ===============================================================================
# delete_file - delete file from the receiver folder. if the file/dir exist delete it
#
# path - the path of the file that will delete
# ===============================================================================
def delete_file(path):
    # if the file exist
    if os.path.exists(path):
        # remove the file
        os.remove(path)



# ===============================================================================
# read_file - read file from file that exist in the receiver folder
#
# path - the path of the file
# the func return the file of bytes
# ===============================================================================
def read_file(path):
    # the size of the read bytes
    buffer_size = 100000

    # the all file
    all_file = b''
    try:
        file = open(path, 'rb')
        while True:
            file_bytes = file.read(buffer_size)

            # add the bytes that read
            all_file = all_file + file_bytes
            if not file_bytes:
                break
        file.close()
    except:
        pass

    # return the file bytes
    return all_file


# ===============================================================================
# send_modify - the func send to send file - the func here for distinguish the commands
# that got
#
# command - the command from the sender
# path - the path of the file
# socket - the connection to the receiver
# ===============================================================================
def send_modify(command, path, socket):
    send_file(command, path, socket)


# ===============================================================================
# receive_modify - the func receive the file check if the file changed
# if the file changed override the file else we changed nothing
#
# full_path - the path of the file that we need to check
# socket - the connection to the server
# ===============================================================================
def receive_modify(full_path, socket):
    get_file = 0

    # send the sender to send a file
    socket.send((get_file).to_bytes(4, "big"))

    # send the size of the file
    size_bytes = socket.recv(4)
    size_server = int.from_bytes(size_bytes, "big")

    # variable to save the file that got from sender
    server_file = b''

    try:
        while True:

            # the bytes that we got from server
            current_server_bytes = socket.recv(min(BUFFER_SIZE, size_server))

            # add the bytes to variable- save the file that got
            server_file = server_file + current_server_bytes

            # the len of the bytes already read
            length = len(current_server_bytes)

            # the size of the file that left to get
            size_server = size_server - length

            # if there are no more bytes break
            if size_server == 0:
                break

        # open the file that already exist in the receiver
        client_file = read_file(full_path)

        # check if the content are equal to the content that got from server
        if client_file != server_file:
            # if the content is difference override the old file and write new one
            client_file = open(full_path, 'wb')
            client_file.write(server_file)
            client_file.close()


    except:
        pass


# ===============================================================================
# move_dir_file - rename files and dirs
#
# src_path - the path of the main dir
# local_path - the path of the file/dir inside the main folder
# ===============================================================================
def move_dir_file(src_path, local_path):
    try:

        # split the name of the file/dir that changed and the new name
        src, dst = local_path.split(SEPARATOR)

        # create the path of the dir/file
        src = os.path.join(src_path, src)

        # create the path of the dir/file after the name change
        dst = os.path.join(src_path, dst)

        # change the name of teh dir/file
        os.rename(src, dst)

    except:
        pass


# ===============================================================================
# update_list - add command to the list
#
# command - the command we want to add
# list - the list we want to add the command to it
# ===============================================================================
def update_list(command, list):
    list.append(command)


# ===============================================================================
# send_update - the func send the changes that done from list to the receiver . for changes of create
# or modify files the func send the new file. for others commands it send the command and the
# receiver did the command. in the end the func send the list done
#
# list- the list that the sender did
# socket - the connection tho the receiver
# src_path - the path of the sender - for ability to send files
# ===============================================================================
def send_update(list, socket, src_path):
    empty_list = 0
    shrink_modifies(list)
    shrink_commands(list)
    shrink_deletes(list)
    # moving all commands in list
    for command in list:

        # if the command it to create file
        if command[:2] == "cf":

            # find the path of the sender folder
            absolute_path = os.path.join(src_path, command[2:])

            # send the len of the command
            socket.send((len(command.encode()).to_bytes(4, "big")))

            # send the command
            socket.send(command.encode())

            # send the file to the receiver
            send_file(command, absolute_path, socket)

        # if the command it to modify file
        elif command[:2] == "zf":
            # find the path of the sender folder
            absolute_path = os.path.join(src_path, command[2:])

            # send the len of the command
            socket.send((len(command.encode()).to_bytes(4, "big")))

            # send the command
            socket.send(command.encode())

            # send the file to the receiver
            send_modify(command, absolute_path, socket)

        # for all the others commands
        else:
            #
            socket.send((len(command.encode())).to_bytes(4, "big"))
            socket.send(command.encode())

    # clear the list
    list.clear()

    # send the that the list empty
    socket.send(empty_list.to_bytes(4, "big"))
