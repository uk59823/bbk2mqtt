# bbk2mqtt
Converter for reading JSON from BBK and sending the data via MQTT build as Docker Container.
Many thanks for the based script to [Thomas B.](https://github.com/binderth/mowas_mqtt)


## functionality
The script searches for Identifiers of your AGS in all of warnings from the german Bundesamt für Bevölkerungsschutz und Katastrophenschutz for your regions.
It subsumizes the findings in a complete JSON in the nodes
* bbk.mowas: Modulares Warnsystem
* bbk.biwapp: Bürgerinfo und Warn-App
* bbk.katwarn: KATWARN
* bbk.lhp: Länderübergreifendes Hochwasserportal
* bbk.dwd: Deutscher Wetterdienst

The docker image you can find [here](https://hub.docker.com/r/ukrae/bbk2mqtt "bbk2mqtt on docker").

## Prerequisites
* living in Germany ;) so additional the Timezone is set in the container to Europe/Berlin
* knowing your "Amtlicher Gemeindeschlüssel (AGS)" for your Landkreis (not city!), available from [Statistisches Bundesamt](https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/Administrativ/04-kreise.html)

## MQTT-Settings 
* MQTT_BROKER: IP-Address (or FQN) of your MQTT Broker (*default: 'localhost'*)
* MQTT_PORT: Port for your Broker (*default: 1883*)
* MQTT_QOS: QOS-level for the message (*default: 2*)
* MQTT_RETAIN: True/False for telling the MQTT-server to retain the message or discard it (*default: True*)
* MQTT_TOPIC: MQTT topic for the JSON (*default: 'main_uk/bbk'*)
* MQTT_USER: Username for the broker (*leave empty for anonymous call*)
* MQTT_PASSWORD: Password for the broker (*leave empty for anonymous call*)
* MQTT_CLIENTID: ClientID for the broker to avoid parallel connections (*default: 'bbk_mqtt'*)

## bbk2mqtt.ini
The file is stored in the subdirectory 'ini' 
To get access to the ini-File in the container you can mount a local file into the container. The ini-File in the container is placed here: '/ini/bbk2mqtt.ini' 

# Variables in bbk2mqtt.ini settings file
```
[General]
loglevel: INFO
interval: 30
```
* loglevel: *INFO* shows only when ready, *DEBUG* shows more debug information to track down errors (*default: 'INFO')
* interval: between two requests there is an interval in minutes (*default: 30*)

```
[AGS]
059580000000: Hochsauerlandkreis
091720000000: Berchtesgadener Land
```
* Section for interested Landkreise, the section is described as '[AGScode]: [Landkreis]'. You can add multiple if you are interested in.
* Note 'AGScode' is the AGS (Amtlicher Gemeindeschlüssel) for your interested Landkreis!, there's only JSONs available for Landkreise, not cities or other smaller entities. The AGScode must be 12 digits long, if yours is shorter, please add enough "0" for 12 digits.

```
[Base]
url: https://warnung.bund.de/bbk.status/status_{}.json
nodes: mowas,biwapp,katwarn,lhp,dwd
```
* url: Base Url for reading the Messages for your AGScode
* nodes: List of known nodes for checking of new/unknown nodes (*default: 'mowas,biwapp,katwarn,lhp,dwd'*)

```
[Source_URL]
mowas: https://warnung.bund.de/bbk.mowas/gefahrendurchsagen.json
biwapp: https://warnung.bund.de/bbk.biwapp/warnmeldungen.json
katwarn: https://warnung.bund.de/bbk.katwarn/warnmeldungen.json
lhp: https://warnung.bund.de/bbk.lhp/hochwassermeldungen.json
dwd: https://warnung.bund.de/bbk.dwd/unwetter.json
```
* Section for the relevant detailed Messages from the different providers. If you have no interest f.e. for "Unwetter-Meldungen" then comment it out

```
[JSON]
pop: polygon,geocode
```
* pop: to delete the json path of "polygon" and/or "geocode" in the 'info'-part of the message

```
[Filter]
searchterm: 
```
* searchterm: delete an complete message that contains this word, if the value is not set nothing will be delete 

```
[Filter_Out]
category: Health
severity: Minor
headline:Corona
```
* section to filter out complete messages if the json path '*info'/'[variable]*' contains the value

## output on your mqtt broker
    MQTT_TOPIC/interval
    MQTT_TOPIC/internet_response
    MQTT_TOPIC/subtopic/county
    MQTT_TOPIC/subtopic/count
    MQTT_TOPIC/subtopic/alert
    MQTT_TOPIC/subtopic/update
* **MQTT_TOPIC** is defined in the docker environment, **subtopic** is the *AGScode* defined in the inifile.
* ../county: name of the [Landkreis], see inifile-section *AGS*
* ../count: filtered number of messages for this Landkreis 
* ../alert: list of messages 
* ../update: datetime of last update
 
(all dates ISO8601 formatted)
