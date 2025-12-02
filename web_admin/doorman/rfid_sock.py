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
# do:
# returns True/False
# tested and works with
# no ard conn (times out, false)
# good update
# no network server present
# other test cases(?????)


#
# 
#
def make_connection(host = HOST, port = PORT):
    """
    Make a socket 
    
    Args:
        Host
        Port

    Returns:
        socket or false
    """
    try:
      logger.info("make socket")
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
      logger.info(f"[CREATE SOCKET ERROR]  {e}")
      return False
    try:
      logger.info ("connect")
      sock.connect((host,int(port)))
    except socket.error as  msg:
      sys.stderr.write(f"[CONNECT ERROR]  { msg}")
      return False
    finally:
        return sock

def open_fucking_door(password, host = HOST, port = PORT):
    """
        Send open command to Door

        Args:
            host
            port

        Returns: True or False    
    """
    logger.info("make socket")
    sock = make_connection( host, port)
    if (sock == False):
        return False
    try:
        logger.info (F"send password: {password}")
        msg = F"o 1${password}\r\n"
        logger.info(F'msg is : {msg}')
        sock.send(msg.encode('utf-8'))
    except socket.error as msg:
        logger.info(f"[SEND ERROR] { msg}")
        return False
    # at this point essentially fuck it.
    finally:
        sock.close()
        return True

newpat =  re.compile(r"Tag: (\S+) successfully added with mask:(\S+)", re.M)
foundpat = re.compile(r"Tag: (\S+) found and updated to mask:(\S+)", re.M)

def modify_user(host, port, tag, mask, password):
    """
    Add or Modify RFID tag # and mask in EEPROM

    Args:
        host
        port
        RFID tag #
        mask
        password

    Returns True or False
        
    """
    
    logger.info("modify_user ")
    logger.info(f"host: {host} port: {port}")
    data_str = F"m {tag} {mask}${password}\r\n"
    logger.info(f"send data_str: {data_str}")
 
    client_rfid = make_connection(host, port)
    if (client_rfid == False):
        return False

    logger.info("client_rfid connected")
    client_rfid.sendall(data_str.encode('utf-8'))
    data_recv = client_rfid.recv(1024)
    returned_data_str = data_recv.decode("utf-8")
    logger.info(f"Receved from RFID {returned_data_str}")
    client_rfid.close()
    logger.info("Socket closed.")

    logger.info(F"returned_data_str: {returned_data_str}")
  
    success = False

    match = newpat.search(returned_data_str)
    if match:
        logger.info("tag: %s mask %s\n" % (match.group(1), match.group(2)))
        success = True
        return success
    
    match =foundpat.search(returned_data_str)
    if match:
        logger.info("tag: %s mask %s\n" % (match.group(1), match.group(2)))
        success = True
        return success

    logger.info(success)
    return success


"""
Remove tag from EEPROM
"""


removed_pat =  re.compile(r"User deleted for tag: (\S+)", re.M)
not_found_pat = re.compile(r"Tag: (\S+) found and updated to mask:(\S+)", re.M)

def remove_rfid_from_EEPROM(host, port, tag,  password):
    """
    Remove RFID tag # from EEPROM

    Args:
        host
        port
        RFID tag #
        password
    Returns True or False
    """
    logger.info(f"remove rfid from EEPROM: {tag}  ")
    logger.info(f"host: {host} port: {port}")
    data_str = F"r {tag} {password}\r\n"
    logger.info(f"send data_str: {data_str}")
    sock = make_connection(host, port)
    if ( sock == False):
        return False
    
    logger.info("client_rfid connected")
    sock.sendall(data_str.encode('utf-8'))
    data_recv = sock.recv(1024)
    returned_data_str = data_recv.decode("utf-8")
    logger.info(f"Receved from RFID {returned_data_str}")
    sock.close()
    logger.info("Socket closed.")

    logger.info(F"returned_data_str: {returned_data_str}")
  
    success = False

    match = removed_pat.search(returned_data_str)
    if match:
        logger.info("tag: %s removed from EEPROM\n" % (match.group(1)))
        success = True
        return success
    
    match =not_found_pat.search(returned_data_str)
    if match:
        logger.info("tag: %s not found in EEPROM\n" % (match.group(1)))
        success = False
    

    logger.info(success)
    return success #False

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
"""
if __name__ == '__main__':
    #send_command("m 222222 1$notpassword\r\n")
    modify_user(HOST, PORT, "222222", "1", "notpassword")
    sys.exit(0)
