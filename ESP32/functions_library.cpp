/* =============================================================================
                           Hammer node functions library
   ============================================================================= */

// Header file dependencies
#include "functions_library.h"
#include <driver/pcnt.h>
#include <global_declarations.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

// Button state check with debounce. For button with pullup.
void check_button()
{
  uint8_t reading1 = digitalRead(pin.test_button);
  if (reading1 != lastButtonState)
  {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay)
  {
    if (reading1 != buttonState)
    {
      buttonState = reading1;

      // Flag activatet upon button state activation
      if (buttonState == LOW)
      {
        testStart = true;
        tft.fillScreen(ST77XX_BLACK);
        tft.setCursor(0, 0);
        tft.setTextSize(1);
        tft.println("Test start manually");
      }
    }
  }

  lastButtonState = reading1;

  uint8_t reading2 = digitalRead(pin.mag_relay_button);
  if (reading2 != lastButtonState2)
  {
    lastDebounceTime2 = millis();
  }

  if ((millis() - lastDebounceTime2) > debounceDelay)
  {
    if (reading2 != buttonState2)
    {
      buttonState2 = reading2;

      // Flag activatet upon button state activation
      if (buttonState2 == LOW)
      {
        magDrop = true;
        tft.fillScreen(ST77XX_BLACK);
        tft.setCursor(0, 0);
        tft.setTextSize(1);
        tft.println("Magnet released manually");
      }
    }
  }

  lastButtonState2 = reading2;
}

// Function for running the test
void run_test()
{
  firstRead = true; // Reset filter for accelerometer

  //calibrateOffset(); // Calibrate accelerometer
  totalPulses = 0; // Reset pulse counter variable for encoder before test series
  pcnt_counter_clear(PCNT_UNIT); // Clear pulse counter before test

  //digitalWrite(pin.relay, HIGH);
  delay(100); // Delay to make sure Arduino receives and acts on activating magnet
  raise_arm(); // Raise arm
  Serial.println("raise_arm() completed");

  // Create Json structure
  JsonDocument data;
  data.clear(); // Tøm JSON-strukturen
  data["encoder"] = JsonArray();
  data["test_time_ms"] = JsonArray();
  data["temp"] = JsonArray();
  data["hum"] = JsonArray();

  Serial.println("Starter test...");
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextSize(1);
  tft.println("Test start");

  //digitalWrite(pin.relay, LOW); // activating relay, dropping hammer to start test
  //delay(500);                   // Delay giving time for electromagnet spool to burn out, unneccesary 
  Serial.println("Relay pin set to LOW");

  startTime = millis();


  // Starting data collection
  Serial.println("Test while loop");
  while ((millis() - startTime) < data_collection_time)
  {
    get_data(data);
    vTaskDelay(pdMS_TO_TICKS(step_length));
  }
  data["temp"].add(bme.readTemperature());
  data["hum"].add(bme.readHumidity());
  
  // Data collection complete, publish to serial monitor and mqtt
  Serial.println("Data Collection Complete:");
  serializeJson(data, Serial); // Data to serial monitor for debug
  Serial.println();            // avslutt med newline
  // publish_json(data);                // Publish data to MQTT
  system_reset(); // Prepare system for new test
  testStart = false; // Reset flag
}

double readEncoderAngle()
{

  int16_t delta = 0; // Num of pulses counted since last run

  pcnt_counter_pause(PCNT_UNIT);
  pcnt_get_counter_value(PCNT_UNIT, &delta);  // Read and move value to delta
  pcnt_counter_clear(PCNT_UNIT); // Necessary to prevent HW counter overflow
  pcnt_counter_resume(PCNT_UNIT);

  // Accumulate new pulses
  totalPulses += (long)delta;

  // Konverter totalpuls til vinkel i grader eller radianer
  // I grader: (totalPulses / CPR) * 360.0
  // I radianer: (totalPulses / CPR) * TWO_PI
  angleRad = ((double)totalPulses / (double)CPR) * 360; // Angle read is double
  return angleRad;
}

// Takes measurement, stores data in Json
void get_data(JsonDocument &data)
{
  // Get angle data and add to JSON
  double angle = readEncoderAngle();
  data["encoder"].add(angle);

  // Read accelerometer, nofilter
  //sensors_event_t accel, gyro, temp;
  //mpu.getEvent(&accel, &gyro, &temp);

  // Offset from calibration 
  //float relZ = accel.acceleration.z - offsetZ;

  // Add data to Json
 // data["accelerometer"].add(relZ);
  data["test_time_ms"].add(millis() - startTime); // Add timestamp
}

// Function to control the process after a test
// Legg til kalibrering
void system_reset()
{
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextSize(1);
  tft.println("Ready for test");
}

void calibrateOffset()
{
  Serial.print("Kalibrerer...");
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextSize(1);
  tft.println("Kalibrerer akselerometer");
  sensors_event_t accel, gyro, temp;
  long sumZ = 0;
  for (int i = 0; i < CALIB_SAMPLES; i++)
  {
    mpu.getEvent(&accel, &gyro, &temp);
    sumZ += accel.acceleration.z;
    vTaskDelay(pdMS_TO_TICKS(10));
  }
  offsetZ = sumZ / float(CALIB_SAMPLES);
  Serial.print(" ferdig. offsetZ = ");
  Serial.println(offsetZ);
  isCalibrated = true;
}

// Function for raising arm with stepper motor
void raise_arm()
{
   
    // Tøm gamle semaforer
  xSemaphoreTake(extSenseSem, 0);
  xSemaphoreTake(retSenseSem, 0);

  // 1) Start bevegelsen
  digitalWrite(pin.arm_cmd_sign, HIGH);
  vTaskDelay(pdMS_TO_TICKS(500));
  digitalWrite(pin.arm_cmd_sign, LOW);

  Serial.println("Hever arm......");
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextSize(1);
  tft.println("Hever arm......");

 

  // 2) Vent på at ext‐sensoren gir signal
  Serial.println("Venter på arm hevet sensor");
  if (xSemaphoreTake(extSenseSem, portMAX_DELAY) == pdTRUE)
  {
    Serial.println("Ext-sensor trigget!");
  }

  vTaskDelay(pdMS_TO_TICKS(4000));
  xSemaphoreTake(retSenseSem, 0);
  
  // 3) Vent på at retur‐sensoren gir signal
  Serial.println("Venter på linear aktuator reset");
  if (xSemaphoreTake(retSenseSem, portMAX_DELAY) == pdTRUE)
  {
    Serial.println("Ret-sensor trigget!");
  }

  Serial.println("Arm hevet");
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextSize(1);
  tft.println("Arm hevet");
  vTaskDelay(pdMS_TO_TICKS(1000));
}

// Publis to MQTT server
void publish_json(JsonDocument &data)
{
  String jsonString;
  serializeJson(data, jsonString); // Json to string for mqtt
  Serial.print("JSON size: ");
  Serial.println(jsonString.length());

  if (!client.connected())
  {
    Serial.println("MQTT er ikke tilkoblet. Prøver å koble til...");
    // Kall funksjonen for å gjenopprette tilkoblingen
    reconnect();
  }

  bool publishSuccess = client.publish("node/hammer", jsonString.c_str());
  onMqttPublishCallback(publishSuccess);
}

// Callback for MQTT send suksess
void onMqttPublishCallback(bool success)
{
  if (success)
  {
    Serial.println("MQTT publish succeeded!");
    tft.println("MQTT publish succeeded!");
  }
  else
  {
    Serial.println("MQTT publish failed!");
    tft.println("MQTT publish failed!");
  }
}

void setup_lcd()
{
  digitalWrite(pin.lcd_backlight, HIGH);
  Serial.println("SPI begin");
  SPI.begin(pin.CLK, /* MISO (bruk -1 hvis ikke i bruk) */ -1, pin.MOSI, pin.CS_lcd);

  Serial.println("TFT begin");
  // Initialiser skjermen med riktig oppstartssekvens.
  // Bruk INITR_BLACKTAB for de fleste ST7735 med svart tab, alternativt INITR_GREENTAB om skjermen din er av denne typen.
  tft.initR(INITR_BLACKTAB);

  Serial.println("TFT init");
  tft.setRotation(1);
  tft.fillScreen(ST77XX_BLACK);

  // Test tegning
  Serial.println("TFT test draw");
  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);
  tft.setTextSize(2);
  tft.setCursor(0, 0);
  tft.println("Oppstart");
}
