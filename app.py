from flask import Flask, request, jsonify
# import am43
import sqlite3
import os

app = Flask(__name__)
app.config["DEBUG"] = True


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
        return msg
        conn.close()

def get_blinds_from_db():
    try:
        conn = sqlite3.connect('am43.db')
        cursor = conn.execute("SELECT * FROM blinds")
        blinds = []
        for row in cursor:
            blinds.append(row)
        return blinds
    except:
        print("Error getting blinds from database")
        return None
    finally:
        conn.close()

#may not be needed or need to be updated?
def update_blind_in_db(name, mac_address, battery, position, light):
    try:
        conn = sqlite3.connect('am43.db')
        conn.execute("UPDATE blinds SET name=?, mac_address=?, battery=?, position=?, light=? WHERE name=?", (name, mac_address, battery, position, light, name))
        conn.commit()
        msg="Successfully updated blind in database"
        print(msg)
    except:
        msg="Error updating blind in database, performing rollback"
        print(msg)
        conn.rollback()
    finally:
        return msg
        conn.close()

@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/blinds', methods=['GET'])
def get_blinds():
    return jsonify(get_blinds_from_db())

@app.route('/blinds', methods=['POST'])
def add_blind():
    if not request.args or not 'mac_address' in request.args or not 'name' in request.args:
        print(request.args)
        return "Invalid Request", 400

    input_blind_to_db(request.args['name'], request.args['mac_address'], 0, 0, 0)
    return jsonify(get_blinds_from_db()), 201

@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404

print ("hello world!")