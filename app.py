from datetime import datetime
from flask import Flask, request, jsonify
import am43
import sqlite3
import os
from subprocess import Popen
import json
import threading
import time


app = Flask(__name__)
app.config["DEBUG"] = True
app.run(host='0.0.0.0')


try:
    conn = sqlite3.connect('am43.db')
    print("Opened database successfully")
except:
    print("Error opening database")
    exit()

conn.execute('''CREATE TABLE IF NOT EXISTS "blinds" (
        "name"	TEXT,
        "mac_address"	TEXT,
        "battery"	INTEGER,
        "position"	INTEGER,
        "light"	INTEGER
    );''')

conn.close()


def ping_blind(mac_address=None, blind=None, intended_position=None):
    conn = sqlite3.connect('am43.db')
    try:
        if blind is None and mac_address is None:
            blinds_list = get_blinds_from_db()
            mac_list = []
            blinds_list = json.loads(blinds_list)
            for blind in blinds_list:
                mac_list.append(str(blind['mac_address']))
            print(mac_list)
            blinds = am43.search(*mac_list)
        else:
            blinds = [am43.search(mac_address)]
        print(blinds)
        for blind in blinds:
            properties = blind.get_properties()
            if intended_position is not None and int(properties.position) not in range(int(intended_position) - 5, int(intended_position) + 5):
                blind.set_position(int(intended_position))
                msg = "Not all blinds were set correctly retrying in 5 seconds: Blind %s, position %s" % (blind._device.addr, str(intended_position))
                print(msg)
                threading.Thread(target=set_blind_position, args=(blind._device.addr, intended_position, True)).start()
            else:
                conn.execute("UPDATE blinds SET battery=?, position=?, light=? WHERE mac_address=?", (properties.battery, properties.position, properties.light, blind._device.addr.upper()))
                conn.commit()
                msg="Successfully updated blind in database"
                print(msg)
                print(properties)
            blind.disconnect()
    except Exception as e:
        msg="Error updating blind in database, performing rollback"
        print(msg)
        print(e)
        conn.rollback()
    finally:
        conn.close()
        print("Finished updating blind db")
        return msg
        

def input_blind_to_db(name, mac_address, battery, position, light):
    try:
        conn = sqlite3.connect('am43.db')
        conn.execute("INSERT INTO blinds VALUES (?, ?, ?, ?, ?)", (name, mac_address, battery, position, light))
        conn.commit()
        msg="Successfully added blind to database"
        print(msg)
    except:
        msg="Error adding blind to database, performing rollback"
        print(msg)
        conn.rollback()
    finally:
        conn.close()
        return msg
        

def get_blinds_from_db():
    try:
        conn = sqlite3.connect('am43.db')
        conn.row_factory = sqlite3.Row
        blinds = conn.execute("SELECT * FROM blinds").fetchall()
        # cursor = conn.execute("SELECT * FROM blinds")
        # blinds = []
        # for row in cursor:
        #     blinds.append(row)
        return json.dumps([dict(ix) for ix in blinds])
    except:
        print("Error getting blinds from database")
        return None
    finally:
        conn.close()

def set_blind_position(mac_address, position, retry=False):
    conn = sqlite3.connect('am43.db')
    try:
        blind = am43.search(mac_address)
        print(blind)
        blind.set_position(int(position))
        msg="Successfully set blind position"
        print(msg)
        conn.execute("UPDATE blinds SET position=? WHERE mac_address=?", (position, mac_address))
        conn.commit()
        print("Successfully updated blind in database")
        if retry:
            time.sleep(5)
            ping_thread = threading.Timer(60, ping_blind, args=(mac_address, None, position))
            ping_thread.start()
            print("thread started, waiting to ping")
    except Exception as e:
        msg="Error setting blind position"
        print(msg)
        print(e)
    finally:
        conn.close()
        blind.disconnect()
        return msg

def set_all_blinds_position(position):
    start_time = time.time()
    blinds_list = get_blinds_from_db()
   
    mac_list = []
    blinds_list = json.loads(blinds_list)
    for blind in blinds_list:
        mac_list.append(str(blind['mac_address']))
    print(mac_list)
    try:
        blinds = am43.search(*mac_list)
        for blind in blinds:
            conn = sqlite3.connect('am43.db') 
            try:  
                blind.set_position(int(position))
                msg="Successfully set blind position"
                print(msg)
                conn.execute("UPDATE blinds SET position=? WHERE mac_address=?", (position, blind._device.addr))
                conn.commit()
                print("Successfully updated blind in database")
            except Exception as e:
                msg="Error setting blind position"
                print(msg)
                print(e)
            finally:
                conn.close()
                blind.disconnect()
    except Exception as e:
        print("Error when trying to set all blinds position")
        print(e)
        return False
    print("Total time: " + str(round((time.time() - start_time), 2)) + " seconds")
    return True
    
# ping_thread = threading.Timer(30, ping_blind, [request.json['mac_address']])

@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/blinds', methods=['GET'])
def get_blinds():
    return get_blinds_from_db()

@app.route('/blinds', methods=['POST'])
def add_blind():
    if not request.json or not 'mac_address' in request.json or not 'name' in request.json:
        print(request.json)
        return "Invalid Request", 400

    input_blind_to_db(request.json['name'], request.json['mac_address'], 0, 0, 0)
    ping_blind(request.json['mac_address'])
    return get_blinds_from_db(), 201

@app.route('/blinds/set', methods=['POST'])
def set_position():
    for arg in request.json:
        print(arg)
    print(request.json)
    if not request.json or not 'position' in request.json and not 'mac_address' in request.json:
        print(request.json)
        return "Invalid Request", 400
    elif not 'mac_address' in request.json and 'position' in request.json:
        set_all_blinds_position(request.json['position'])
        ping_thread = threading.Timer(60, ping_blind, args=(None, None, request.json['position']))
        ping_thread.start()
        print("thread started, waiting to ping")
        return get_blinds_from_db(), 201
    else:
        set_blind_position(request.json['mac_address'], request.json['position'])
        ping_thread = threading.Timer(30, ping_blind, [request.json['mac_address']])
        ping_thread.start()
        print("thread started, waiting to ping")
        
        # ping_blind(request.json['mac_address'])
        return get_blinds_from_db(), 201

@app.route('/blinds/update', methods=['GET'])
def force_update():
    print("printing args")
    if request.json and 'mac_address' in request.json:
        print(request.json['mac_address'])
        # for arg in request.args:
        print("pinging " + request.json['mac_address'])
        ping_blind(request.json['mac_address'])
    else:
        print("pinging all")
        ping_blind()
    return get_blinds_from_db(), 201

@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404

print ("hello world!")
