#!/usr/bin/env python3
# -*- coding: utf-8 -*
import os                                           # using the OS
import urllib.request
import requests                                     # requesting information
import json                                         # working with JSON
import configparser                                 # working with INI
import paho.mqtt.client as mqtt				        # using MQTT-client
import time
import datetime
from requests.exceptions import ConnectionError     # errors in requests

broker = 'localhost'
inifile = 'ini/bbk2mqtt.ini'

# MQTT-Settings
mqtt_ipaddress = os.getenv('MQTT_BROKER', broker)
mqtt_user = os.getenv('MQTT_USER', '')
mqtt_pass = os.getenv('MQTT_PASSWORD', '')
mqtt_topic = os.getenv('MQTT_TOPIC', 'main_uk/bbk')
mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
mqtt_qos = int(os.getenv('MQTT_QOS', '2'))
mqtt_retain = eval(os.getenv('MQTT_RETAIN', 'True'))
mqtt_clientid = os.getenv('MQTT_CLIENTID', 'bbk_mqtt')


def readIniSettings():
    # read settings from mowas_mqtt.ini
    ApplicationDir = os.path.dirname(os.path.abspath(__file__))
    ReadSettings = os.path.join(ApplicationDir, inifile)
    Settings = configparser.ConfigParser()
    Settings.read(ReadSettings)

    # Log-Level
    global loglevel
    loglevel = Settings.get("General", "loglevel")
    # Interval between two requests
    global interval
    interval = int(Settings.get("General", "interval"))
    # Json pop
    global popJson
    popJson = Settings.get("JSON", "pop")

    # Filter
    global filterSearchterm
    global filterItems
    filterSearchterm = Settings.get("Filter", "searchterm")
    filterItems = Settings.items("Filter_Out")

    # Landkreis(e) AGS
    global ags
    ags = Settings.items("AGS")

    # setting API information sort of from https://warnung.bund.de/bbk.config/config_rel.json
    global baseUrl
    baseUrl = Settings.get("Base", "url")

    # existing nodes for checking unknown nodes
    global nodes
    nodes = Settings.get("Base", "nodes")

    # Urls for detailed informaton
    global json_URLs
    json_URLs = Settings.items("Source_URL")


def connect():
    host = 'http://google.com'
    try:
        urllib.request.urlopen(host)  # Python 3.x
        return True
    except:
        return False


def on_connect(client, userdata, flags, rc):
    # Connect to MQTT-Broker
    if rc != 0:
        print("Connection Error to broker using Paho with result code " + str(rc))


def send_mqtt_paho(message, topic):
    # send MQTT message
    if (loglevel == "DEBUG"):
        print("Broker with Client-ID '{}', Port '{}', User '{}', Passwort '{}' and QOS '{}', Retain '{}'".format(
            mqtt_clientid, mqtt_port, mqtt_user, mqtt_pass, mqtt_qos, mqtt_retain))
        print("Sending message: '{}'".format(message))
    mqttclient = mqtt.Client(mqtt_clientid)
    mqttclient.on_connect = on_connect
    if mqtt_user != "":
        mqttclient.username_pw_set(mqtt_user, mqtt_pass)
    mqttclient.connect(mqtt_ipaddress, mqtt_port, 60)
    mqttclient.loop_start()
    mqttpub = mqttclient.publish(
        topic, payload=message, qos=mqtt_qos, retain=mqtt_retain)
    mqttclient.loop_stop()
    mqttclient.disconnect()


def get_json_as_dict(url):
    # GET JSON from URL
    global requestError
    headers = {'Accept': '*/*',
               'Content-Type': 'application/json; charset=utf-8',
               'User-Agent': 'MOWAS-MQTT'}
    # make request, gracefully with error
    try:
        if (loglevel == "DEBUG"):
            print("request URL: {} - {}".format(str(url), str(headers)))
        r = requests.get(url, headers=headers)
    except ConnectionError as e:
        requestError = True
        print("Connection Error")
        print(e)
        return json.loads('{"data": {"Connection Error": 1, "URL": "' + url + '", "error": "' + e + '"}}')
    # wenn HTTP-StatusCode not 200
    if r.status_code != 200:
        requestError = True
        print("HTTP Error")
        print(str(r.status_code))
        return json.loads('{"data": {"HTTP Error": 1, "URL": "' + url + '", "error": "' + str(r.status_code) + '"}}')
    # JSON to dict, gracefully with error
    try:
        data = json.loads(r.content.decode())
    except ValueError as e:
        requestError = True
        print("JSON Error")
        print(e)
        return json.loads('{"data": {"JSON Error": 1, "URL": "' + url + '", "error": "' + e + '"}}')
    requestError = False
    return data


def search_in_dict(values):
    # find a term in a dict
    ret = False
    if (filterSearchterm == "" and len(filterItems) == 0):
        return ret

    for k in values:
        if loglevel == "DEBUG":
            print(values)
            print(k)

        if (filterSearchterm != ""):
            for v in values[k]:
                if filterSearchterm in v:
                    ret = True

        if (k == 'info' and len(filterItems) > 0):
            for l in values[k][0]:
                for w in filterItems:
                    if (l == w[0] and w[1] in values[k][0][l]):
                        ret = True
    return ret


def getItemValue(itemlist, itemname):
    # get the value to variable
    for k in itemlist:
        if k[0] == itemname:
            return k[1]


def checkUnknownBuckets(buckets):
    # check if unknown buckets exist
    for i in range(len(buckets)):
        keys = buckets[i]['bucketname'].split('.')
        nodeexist = keys[1] in nodes
        if nodeexist == False:
            send_mqtt_paho("Unknown Node: '" + buckets[i]['bucketname'] + "' search for Url and add it in ini-File.",
                           mqtt_topic + '/unknownNode')
    return True


def readMowas(ags_lk):

    # start variables
    buckets_live = {}
    JSONreturn = {}

    dt = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    if connect() != True:
        print("[" + dt + "] - No internet connection")
        send_mqtt_paho('408 Request Timeout (Internet connection)',
                       mqtt_topic + "/internet_response")
        return
    else:
        send_mqtt_paho('200 OK', mqtt_topic + "/internet_response")

    # get JSON from Landkreis as dict
    landkreis_meldungen = get_json_as_dict(baseUrl.format(ags_lk[0]))

    # check, if there's an error with the JSON
    if (requestError == True):
        send_mqtt_paho(json.dumps(landkreis_meldungen),
                       mqtt_topic + '/' + ags_lk[0] + '/error')
        send_mqtt_paho(dt, mqtt_topic + '/' + ags_lk[0] + "/update")
        if loglevel == "DEBUG":
            print(landkreis_meldungen)
        return True

    # check, if there's announcements for the Landkreis
    i = 0

    # checkUnknownBuckets
    checkUnknownBuckets(landkreis_meldungen)

    for bucket in landkreis_meldungen:

        # MOWAS JSON has multiple buckets, currently:
        # 0: bkk.mowas
        # 1: bbk.biwapp
        # 3: bbk.katwarn
        # 4: bbk.lhp
        # 5: bbk.dwd
        keys = bucket['bucketname'].split('.')
        buckets_live[keys[1]] = {}
        if (loglevel == "DEBUG"):
            print("Find Buckets #" + str(i))
        for ref in bucket['ref']:
            # call the URL and find message
            if (loglevel == "DEBUG"):
                print("Add Bucket to JSON: " + ref)
            buckets_live[keys[1]]['ref' + str(i)] = ref
            i = i + 1

    # get the announcements information
    if (loglevel == "DEBUG"):
        print("Add Bucket to JSON: " + ref)
    i = 0

    for buckets in buckets_live:
        if (len(buckets_live[buckets]) > 0):
            # There's announcements for that bucket!
            if (loglevel == "DEBUG"):
                print("open JSON for Bucket: " +
                      getItemValue(json_URLs, buckets))
            announcementJSON = get_json_as_dict(
                getItemValue(json_URLs, buckets))
            if (loglevel == "DEBUG"):
                print("Found Announcements in: " +
                      getItemValue(json_URLs, buckets))
            for meldung, meldewert in (buckets_live[buckets].items()):
                j = 0
                while (j < len(announcementJSON)):
                    if (loglevel == "DEBUG"):
                        print("search Announcement for: " + meldewert)
                    if (announcementJSON[j]["identifier"] == meldewert):
                        if (search_in_dict(announcementJSON[j]) == False):
                            if (loglevel == "DEBUG"):
                                print("Added Announcement for: " + meldewert)
                            JSONreturn[i] = announcementJSON[j]
                            if "polygon" in popJson:
                                JSONreturn[i]['info'][0]['area'][0].pop(
                                    'polygon')
                                try:
                                    JSONreturn[i]['info'][0]['area'].pop(
                                        'polygon')
                                except:
                                    pass
                                for k in range(len(JSONreturn[i]['info'][0]['area'])):
                                    try:
                                        JSONreturn[i]['info'][0]['area'][k].pop(
                                            'polygon')
                                    except:
                                        pass

                            if "geocode" in popJson:
                                JSONreturn[i]['info'][0]['area'][0].pop(
                                    'geocode')
                                try:
                                    JSONreturn[i]['info'][0]['area'].pop(
                                        'geocode')
                                except:
                                    pass
                                for k in range(len(JSONreturn[i]['info'][0]['area'])):
                                    try:
                                        JSONreturn[i]['info'][0]['area'][k].pop(
                                            'geocode')
                                    except:
                                        pass

                    j = j + 1
                i = i + 1

    # Sending final JSON with MQTT
    if loglevel == "DEBUG":
        print("Sending MQTT")

    print(dt + " - Sending JSON to Topic '{}' for '{}'".format(
        mqtt_topic, ags_lk[1]))
    send_mqtt_paho(dt, mqtt_topic + '/' + ags_lk[0] + "/update")
    send_mqtt_paho(len(JSONreturn), mqtt_topic + '/' + ags_lk[0] + "/count")
    send_mqtt_paho(ags_lk[1], mqtt_topic + '/' + ags_lk[0] + "/county")
    send_mqtt_paho(json.dumps(JSONreturn), mqtt_topic +
                   '/' + ags_lk[0] + "/alert")
    send_mqtt_paho(interval, mqtt_topic + "/interval")
    return True


if __name__ == '__main__':
    print('bbk2mqtt started')
    while 1:
        readIniSettings()
        dtStart = datetime.datetime.now()
        for c in range(len(ags)):
            readMowas(ags[c])
        dtEnd = datetime.datetime.now()
        time.sleep(interval*60 - (dtEnd - dtStart).total_seconds())
