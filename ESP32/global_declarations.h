/* =============================================================================
                      Hammer node global declarations header                             
   ============================================================================= */


#ifndef GLOBAL_DECLARATIONS_H
#define GLOBAL_DECLARATIONS_H

// External libraries
#include <Arduino.h>

#include <ArduinoJson.h>
#include <Adafruit_I2CDevice.h>
#include <Wire.h>

#include <Adafruit_GFX.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <SPI.h>
#include <driver/pcnt.h>
//#include <TFT_eSPI.h>
#include <Adafruit_ST7735.h>

// Project custom libraries
#include <functions_library.h>

// Semaforlogikk
#include "freertos/semphr.h"

// Temp og hum
#include <Adafruit_BME280.h>


// Velg PCNT‑unit og channel
#define PCNT_UNIT        PCNT_UNIT_0
#define PCNT_CHANNEL     PCNT_CHANNEL_0

// Grenser for telleren (juster etter behov)
#define PCNT_H_LIM_VAL   (+10000)
#define PCNT_L_LIM_VAL   (-10000)

// Debounce‑filter i µs (ignorer pulser kortere enn dette)
#define PCNT_FILTER_US   (100)



// ------------------ STRUCT FOR PINS ------------------
typedef struct Pins
{
  const int test_button;
  const int relay;
  const int SDA;
  const int SCL;
  const int MOSI;
  const int CLK;
  const int MISO;
  const int CS_lcd;
  const int TFT_RST;
  const int TFT_DC;
  const int lcd_backlight;
  const int mag_relay_button;
  const int encoder_A;
  const int encoder_B;
  const int microswitch;
  const int arm_ext_sens;
  const int arm_ret_sens;
  const int arm_cmd_sign;
} Pins;

// Definer pinner for din skjerm – tilpass disse etter din wiring!
//extern const int TFT_CS;   
extern const int TFT_DC;   
extern const int TFT_RST;  


// "Extern" variables: De _defineres_ i global_declarations.cpp
extern Pins pin;

// Non-blocking timing
extern unsigned long lastReadTime;
extern unsigned long startTime;

// Encoder global variables
extern const long CPR;
extern long totalPulses;
extern double angleRad;

// Semaforlogikk
extern SemaphoreHandle_t extSenseSem;
extern SemaphoreHandle_t retSenseSem;


// Accelerometer with EMA filter
extern Adafruit_MPU6050 mpu;
extern float filter_alpha;
extern bool firstRead;
extern float filteredAccelerometerValue;
extern float offsetZ;                           // Calibration offset
extern bool isCalibrated;                     // Calibration flag
extern const int CALIB_SAMPLES;                  // Calibration samples


// Obj for BME sensor
extern Adafruit_BME280 bme;

// LCD
//extern TFT_eSPI tft;
extern Adafruit_ST7735 tft;



// Parametere
extern const unsigned long data_collection_time;
extern const int data_resolution;
extern const int step_length;

// Debounce-variabler
extern unsigned long lastDebounceTime;
extern unsigned long debounceDelay;
extern bool lastButtonState;
extern bool buttonState;

extern unsigned long lastDebounceTime2;
extern unsigned long debounceDelay2;
extern bool lastButtonState2;
extern bool buttonState2;

#endif // GLOBAL_DECLARATIONS_H