FROM python:3-alpine

RUN apk add --no-cache tzdata
ENV TZ=Europe/Berlin
ENV MQTT_BROKER=localhost
ENV MQTT_PORT=1883
ENV MQTT_QOS=2
ENV MQTT_RETAIN=True
ENV MQTT_TOPIC=main_uk/bbk
ENV MQTT_USER= 
ENV MQTT_PASSWORD= 
ENV MQTT_CLIENTID=bbk_mqtt

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
	
ADD bbk2mqtt.py /
ADD ./ini/bbk2mqtt.ini /ini/

CMD [ "python", "./bbk2mqtt.py" ]