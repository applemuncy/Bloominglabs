#!/usr/bin/env python
import socket
import sys
import select
import re
from django_app.settings import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)

HOST = 'fablabdoor.local'
PORT = 6666
newpat =  re.compile(r"Tag: (\S+) successfully added with mask:(\S+)", re.M)
foundpat = re.compile(r"Tag: (\S+) found and updated to mask:(\S+)", re.M)

# do:
# returns True/False
# tested and works with
# no ard conn (times out, false)
# good update
# no network server present
# other test cases(?????)


def open_fucking_door(password, host = HOST, port = PORT):
    try:
      logger.info("make socket")
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
      logger.info(f"[CREATE SOCKET ERROR]  {e}")
      return False
    try:
      print ("connect")
      sock.connect((host,int(port)))
    except socket.error as  msg:
      sys.stderr.write(f"[CONNECT ERROR]  { msg}")
      return False
# add Exception below
    try:
        print ("send")
        print (password)
        msg = F"o 1${password}\r\n"
        print('msg is :')
        print(msg)
        sock.send(msg.encode('utf-8'))
    except socket.error as msg:
        sys.stderr.write(f"[SEND ERROR] { msg}")
        return False
    # at this point essentially fuck it.
    return True

def modify_user(host, port, tag, mask, password):
    
    logger.info("modify_user ")
    logger.info(f"host: {host} port: {port}")
    client_rfid = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_str = F"m {tag} {mask}${password}\r\n"
    logger.info(f"send data_str: {data_str}")
 
    try:
        client_rfid.connect((host, port))
        logger.info("client_rfid connected")
        client_rfid.sendall(data_str.encode('utf-8'))
        data_recv = client_rfid.recv(1024)
        returned_data_str = data_recv.decode("utf-8")
        logger.info(f"Receved from RFID {returned_data_str}")
 
    except ConnectionRefusedError:
        logger.info(f"Connection refused. Ensure the server is running on {SERVER_HOST}:{SERVER_PORT}")
    except Exception as e:
        logger.info(f"An error occurred: {e}")
    finally:
        # Close the socket
        client_rfid.close()
        logger.info("Socket closed.")
 
    success = False
    match = newpat.search(returned_data_str)
    if match:
        logger.info("tag: %s mask %s\n" % (match.group(1), match.group(2)))
        success = True
 
    logger.info(F"returned_data_str: {returned_data_str}")
    logger.info(success)
    return success


"""
"""
# wow, that's easy
# modify to look for a response(?)
def send_command(command):
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as msg:
      sys.stderr.write(f"[ERROR] { msg}")
      return None
    try:
      sock.connect((HOST, PORT))
    except socket.error as msg:
      sys.stderr.write("f[ERROR] {msg}")
      return None
    
    sock.send(command )

    string = ""
    
    while 1:
        rlist, wlist, elist = select.select( [sock,], [], [], 5 )
    
        # Test for timeout
        if [rlist, wlist, elist] == [ [], [], [] ]:
            print ("Five seconds elapsed.\n")
            break
        else:
            data = sock.recv(1024)
            string = string + data
            print ("select read:%s" % data)
    sock.close()     
    print (string)
    return string

if __name__ == '__main__':
    #send_command("m 222222 1$notpassword\r\n")
    modify_user(HOST, PORT, "222222", "1", "notpassword")
    sys.exit(0)
