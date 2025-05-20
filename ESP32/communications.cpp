/*--------------------------------------------------
    Universal MQTT and WIFI setup code
---------------------------------------------------*/

#include <communications.h>
#include <functions_library.h>
#include <global_declarations.h>

// Wifi
const char *ssid[] = {"iOT Deco", "Zyxel_647D", "Pepperkakehuset 2.etg", "Herverk"};
const char *password[] = {"bre-rule-247", "NJA8EXABJF", "Tangflatavegen2B", "pepperkake"};
int networkIndex = 0;
int num_of_networks_stored = 4; // Update as needed

// MQTT, only one broker will be connected, will try connection according to list
const char *mqtt_servers[] = {"192.168.68.135", "192.168.68.134", "192.168.1.51", "192.168.68.133" }; // List MQTT broker IPs here
int mqttServerIndex = 0;                                                           // Helper variable
int num_mqtt_servers = 4;                                                          // Update according to number of MQTT brokers listed

const char *mqtt_user[] = {"bachAuto", "", "bachAuto"}; // MQTT broker password list, match to server list
const char *mqtt_password[] = {"e2501", "", "e2501"};   // MQTT password list, match to server list
const char *mqtt_client_id = "hammer";                  // This unit client ID
const char *mqtt_subscribe_topic1 = "hammer/actions";   // copy this line and add topics ass necessary. Also edit reconnect() function!
const char *mqtt_subscribe_topic2 = "";
const char *mqtt_publish_topic = "node/hammer";
const char *mqtt_publish_topic2 = "";
WiFiClient espClient;
PubSubClient client(espClient);

// Callback variables specific for an ESP32 unit
volatile bool testStart = false;
volatile bool magDrop = false;

/*---------------------------------------------------
                      Functions
-----------------------------------------------------*/

void setup_wifi()
{
  uint8_t num_of_connections = 20;
  uint8_t counter = 0;
  while (networkIndex < num_of_networks_stored)
  {
    Serial.print("Connecting to WiFi network: ");
    Serial.println(ssid[networkIndex]);
    tft.fillScreen(ST77XX_BLACK);
    tft.setCursor(0, 0);
    tft.setTextSize(1);
    tft.println("Connecting to WiFi network: ");
    tft.println(ssid[networkIndex]);

    WiFi.begin(ssid[networkIndex], password[networkIndex]); // Connection to network according to sequence

    // Wait for connection, try 10 times with 0.5 sec delay each time
    uint8_t attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10)
    {
      vTaskDelay(pdMS_TO_TICKS(500));
      Serial.print(".");
      attempts++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
      Serial.println("\nConnected to WiFi!");
      Serial.print("IP Address: ");
      Serial.println(WiFi.localIP());
      tft.fillScreen(ST77XX_BLACK);
      tft.setCursor(0, 0);
      tft.setTextSize(1);
      tft.println("\nConnected to WiFi!");
      tft.println("IP Address: ");
      tft.println(WiFi.localIP());
      break; // Succesful connection, abort
    }
    else
    {
      Serial.println("\nFailed to connect. Trying next network...");
      tft.fillScreen(ST77XX_BLACK);
      tft.setCursor(0, 0);
      tft.setTextSize(1);
      tft.println("\nFailed to connect. Trying next network...");
      networkIndex++; // Proceed throught the list of networks
    }
  }

  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("Could not connect to any WiFi network, ESP will restart.");
    ESP.restart();
  }
}

void setup_MQTT()
{
  // Will iterate through server list
  bool connected = false;
  for (mqttServerIndex = 0; mqttServerIndex < num_mqtt_servers; mqttServerIndex++)
  {
    Serial.print("Trying MQTT server: ");
    Serial.println(mqtt_servers[mqttServerIndex]);
    tft.fillScreen(ST77XX_BLACK);
      tft.setCursor(0, 0);
      tft.setTextSize(1);
      tft.println("Trying MQTT server: ");
    tft.println(mqtt_servers[mqttServerIndex]);

    client.setServer(mqtt_servers[mqttServerIndex], 1883);
    client.setCallback(callback); // Same callback for all servers

    // Try client connect 3 times until next server, edit if necessary
    for (int attempt = 0; attempt < 3 && !connected; attempt++)
    {
      if (client.connect(mqtt_client_id, mqtt_user[mqttServerIndex], mqtt_password[mqttServerIndex]))
      {
        Serial.println("MQTT connected!");
        tft.fillScreen(ST77XX_BLACK);
      tft.setCursor(0, 0);
      tft.setTextSize(1);
        tft.println("MQTT connected!");
        tft.println("Client ID:");
        tft.println(mqtt_client_id);
        tft.println("Server");
        tft.println(mqtt_servers[mqttServerIndex]);
        connected = true;
      }
      else
      {
        Serial.print("failed, rc=");
        Serial.print(client.state());
        Serial.println(" try again in 2 seconds");
        tft.fillScreen(ST77XX_BLACK);
      tft.setCursor(0, 0);
      tft.setTextSize(1);
      tft.println("failed, rc=");
      tft.println(" try again in 2 seconds");
        delay(2000);
      }
    }

    if (connected)
    {
      // Succesful, break loop
      break;
    }
    else
    {
      Serial.println("Trying next server in the list...");
    }
  }

  if (!connected)
  {
    Serial.println("Could not connect to any MQTT server. ESP will restart");
    ESP.restart();
  }
}

// Connect to MQTT, subscripe to topics if relevant
void reconnect()
{

uint8_t counter = 0;
uint8_t num_of_reconnections_allowed = 20;

  // Loop until we're reconnected or timeout
  while (!client.connected())
  {
    Serial.print("Attempting MQTT connection...");
    tft.fillScreen(ST77XX_BLACK);
      tft.setCursor(0, 0);
      tft.setTextSize(1);
      tft.println("Attempting MQTT connection...");

    // Attempt to connect
    if (client.connect(mqtt_client_id))
    {
      Serial.println("connected");
      tft.println("MQTT connected");

      // Subscribe to topics, add as many as necessary
      client.subscribe(mqtt_subscribe_topic1);
      client.subscribe(mqtt_subscribe_topic2);
    }
    else if (counter > num_of_reconnections_allowed){
      Serial.println("MQTT connection problems, system will restart");
      vTaskDelay(pdMS_TO_TICKS(500));
      ESP.restart();
    }
    else
    {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      vTaskDelay(pdMS_TO_TICKS(5000));
      counter ++;
    }
  }
}

// Callback function for incoming MQTT communication. Unncomment if not necessary.
void callback(char *topic, byte *message, unsigned int length)
{
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;

  for (int i = 0; i < length; i++)
  {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();

  // Add more if statements to control more GPIOs with MQTT if neccesary

  // If a message is received on the topic esp32/output, you check if the message is either "on" or "off".
  // Changes the output state according to the message
  if (String(topic) == mqtt_subscribe_topic1)
  {
    Serial.print("Broker action received");
    if (messageTemp == "start_test")
    {
      Serial.println("Starting test");
      testStart = true;
    }
  }

  if (String(topic) == mqtt_subscribe_topic2)
  {
    Serial.print("Test resaults");
    if (messageTemp == "OK")
    {
      Serial.println("ready");
      // Action (Finished)
    }
    else if (messageTemp == "FAIL")
    {
      Serial.println("off");
      // Action (Test again)
    }
  }
}



void handleSerialCommands() {
  while (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();                   // fjern \r og mellomrom
    if (cmd.equalsIgnoreCase("START")) {
      testStart = true;
      Serial.println("CMD: START mottatt");
    }
    else if (cmd.equalsIgnoreCase("DROP")) {
      magDrop = true;
      Serial.println("CMD: DROP mottatt");
    }
    // legg på flere kommandoer om ønskelig
  }
}