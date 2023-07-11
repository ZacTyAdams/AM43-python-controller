from datetime import datetime
from flask import Flask, render_template, request, jsonify
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

def ping_blind(mac_address=None, group=None, blind=None, intended_position=None):
    print("===In ping_blind===")
    conn = sqlite3.connect('am43.db')
    try:
        blinds_list = get_blinds_from_db()
        mac_list = []
        blinds_list = json.loads(blinds_list)
        for blind in blinds_list:
            if group is None or group == blind['group']:
                print("Intended Position: " + str(intended_position))
                print("Blind Position: " + str(blind['position']))
                if intended_position is not None and intended_position != blind['position']:
                    msg = "Blind may have received another while this thread was in sleep, returning from this call"
                    print(msg)
                    return
                else:
                    print("Blind position is correct, continuing")
                mac_list.append(str(blind['mac_address']))
        print(mac_list)
            
        if len(mac_list) == 1:
            blind = am43.search(*mac_list)
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
        else:
            blinds = am43.search(*mac_list)
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
        

def input_blind_to_db(name, group, mac_address, battery, position, light):
    print("===In input_blind_to_db===")
    try:
        conn = sqlite3.connect('am43.db')
        conn.execute("INSERT INTO blinds VALUES (?, ?, ?, ?, ?, ?)", (name, group, mac_address, battery, position, light))
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
    print("===In get_blinds_from_db===")
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
    print("===In set_blind_position===")
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
    print("===In set_all_blinds_position===")
    start_time = time.time()
    blinds_list = get_blinds_from_db()
   
    mac_list = []
    blinds_list = json.loads(blinds_list)
    for blind in blinds_list:
        mac_list.append(str(blind['mac_address']))
    print(mac_list)
    try:
        if len(mac_list) == 0:
            print("No blinds found")
            return False
        # I know this is ugly but it's late and I need my blinds to work in the morning. Will clean tomorrow?
        elif len(mac_list) == 1:
            blind = am43.search(*mac_list)
            conn = sqlite3.connect('am43.db') 
            try:  
                blind.set_position(int(position))
                msg="Successfully set blind position"
                print(msg)
                print(blind._device.addr)
                print(position)
                result = conn.execute("UPDATE blinds SET position=? WHERE mac_address=?", (position, blind._device.addr.upper()))
                conn.commit()
                print(result)
                print("Successfully updated blind in database")
                print(get_blinds_from_db())
            except Exception as e:
                msg="Error setting blind position"
                print(msg)
                print(e)
            finally:
                conn.close()
                blind.disconnect()
        else:
            blinds = am43.search(*mac_list)
            for blind in blinds:
                conn = sqlite3.connect('am43.db') 
                try:  
                    blind.set_position(int(position))
                    msg="Successfully set blind position"
                    print(msg)
                    conn.execute("UPDATE blinds SET position=? WHERE mac_address=?", (position, blind._device.addr.upper()))
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

def set_group_blinds_position(group, position):
    print("===In set_group_blinds_position===")
    start_time = time.time()
    blinds_list = get_blinds_from_db()
   
    mac_list = []
    blinds_list = json.loads(blinds_list)
    print("Adding blinds belonging to group " + group + " to list")
    for blind in blinds_list:
        print("blind: " + str(blind))
        print("blind group: " + blind['group'])
        if blind['group'] == group:
            mac_list.append(str(blind['mac_address']))
    print("Setting blinds in group " + group)
    print(mac_list)
    try:
        if len(mac_list) == 0:
            print("No blinds found")
            return False
        # I know this is ugly but it's late and I need my blinds to work in the morning. Will clean tomorrow?
        elif len(mac_list) == 1:
            blind = am43.search(*mac_list)
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
        else:
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

if os.path.exists('am43.db'):
    print("Database exists, starting connection")
else:
    print("Database does not exist, creating");
    try:
        conn = sqlite3.connect('am43.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS "blinds" (
            "name"	TEXT,
            "group" TEXT,
            "mac_address"	TEXT,
            "battery"	INTEGER,
            "position"	INTEGER,
            "light"	INTEGER
        );''')
        print("Database created, beginning first time setup")
        while(True):
            name = input("Please enter the name of the blind: ")
            group = input("Please enter the group of the blind: ")
            mac_address = input("Please enter the mac address of this blind: ")
            input_blind_to_db(name, group, mac_address, 0, 0, 0)
            ping_blind(mac_address)
            more_blinds = input("Do you want to add more blinds? (y/n): ")
            if more_blinds == "n":
                break
    except Exception as e:
        print("Error creating database, during setup")
        print(e)


try:
    conn = sqlite3.connect('am43.db')
    print("Opened database successfully")
except:
    print("Error opening database")
    exit()

# conn.execute('''CREATE TABLE IF NOT EXISTS "blinds" (
#         "name"	TEXT,
#         "mac_address"	TEXT,
#         "battery"	INTEGER,
#         "position"	INTEGER,
#         "light"	INTEGER
#     );''')

conn.close()

@app.route('/')
def index():
    # return 'Hello, World!'
    blinds = json.loads(get_blinds_from_db())
    for blind in blinds:
        print(blind["name"])
    # print(blinds[0])
    return render_template('index.html', blinds=blinds)

@app.route('/blinds', methods=['GET'])
def get_blinds():
    return get_blinds_from_db()

@app.route('/blinds', methods=['POST'])
def add_blind():
    print(request.form)
    print(request.form["name"])
    print(request.form["group"])
    print(request.form["mac_address"])
    # print(request.json['name'])
    # print(request.json['mac_address'])
    # if not request.json or not 'mac_address' in request.json or not 'name' in request.json:
    #     print(request.json)
    #     return "Invalid Request", 400

    # input_blind_to_db(request.json['name'], request.json['mac_address'], 0, 0, 0)
    input_blind_to_db(request.form["name"], request.form["group"], request.form["mac_address"], 0, 0, 0)
    # ping_blind(request.json['mac_address'])
    ping_blind(request.form["mac_address"])
    return get_blinds_from_db(), 201

@app.route('/blinds/set', methods=['POST'])
def set_position():
    position = 0
    for arg in request.json:
        print(arg)
    print(request.json)
    try:
        position = int(float(request.json['position']))
        print("Position is: " + str(position))
    except Exception as e:
        print(e) 
    if not request.json or 'position' not in request.json and 'mac_address' not in request.json:
        print(request.json)
        return "Invalid Request", 400
    elif 'group' in request.json and 'position' in request.json:
        print("Closing blinds in group: " + request.json['group'])
        set_group_blinds_position(request.json['group'], position)
        ping_thread = threading.Timer(60, ping_blind, args=(None, request.json['group'], None, position))
        ping_thread.start()
        print("thread started, waiting to ping")
        return get_blinds_from_db(), 201
    elif 'mac_address' not in request.json and 'position' in request.json:
        set_all_blinds_position(position)
        ping_thread = threading.Timer(60, ping_blind, args=(None, None, None, position))
        ping_thread.start()
        print("thread started, waiting to ping")
        return get_blinds_from_db(), 201
    else:
        set_blind_position(request.json['mac_address'], position)
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
