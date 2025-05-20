/*--------------------------------------------------
   Universal MQTT and WIFI setup code header file              
---------------------------------------------------*/


#ifndef COMMUNICATIONS_H
#define COMMUNICATIONS_H

// External dependent libraries
#include <WiFi.h>
#include <PubSubClient.h>
#include <Arduino.h>


// WiFi
extern const char* ssid[];
extern const char* password[];
extern int networkIndex;
extern int num_of_networks_stored;

// MQTT
extern const char* mqtt_servers[];
extern int mqttServerIndex; 
extern int num_mqtt_servers;
extern const char *mqtt_user[];
extern const char *mqtt_password[];

extern const char* mqtt_client_id;
extern const char* mqtt_subscribe_topic1;
extern const char* mqtt_subscribe_topic2;
extern const char* mqtt_publish_topic;
extern const char* mqtt_publish_topic2;

extern WiFiClient espClient;
extern PubSubClient client;

// Callback variables specific for an ESP32 unit
extern volatile bool testStart;
extern volatile bool magDrop;

// Connect to (and maintain connection with) MQTT
void reconnect();

// MQTT callback for incoming messages
void callback(char *topic, byte *message, unsigned int length);

// Configure WiFi
void setup_wifi();

// Set up MQTT client
void setup_MQTT();

// Actions from serial comm
void handleSerialCommands();

#endif // COMMUNICATIONS_H