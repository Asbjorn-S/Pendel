/* =============================================================================
                           Hammer node global declarations                              
   ============================================================================= */



#include <global_declarations.h>
#include <driver/pcnt.h>





// Inputs and outputs
Pins pin = {
  .test_button = 2,   // For starting test manually
  .relay = 5,         // Output to electromagnet relay
  .SDA = 8,           // SDA comm pin for accelerometer
  .SCL = 9,           // SCL  comm pin for accelerometer
  .MOSI = 11,          // TFT SPI MOSI 
  .CLK = 12,           // TFT SPI Clock
  .MISO = -1,          // TFT SPI MISO, ikke i bruk
  .CS_lcd = 10,         // SPI Chip Select for TFT
  .TFT_RST = 6,        // TFT reset
  .TFT_DC = 7,         // TFT Data command
  .lcd_backlight = 4,    // TFT backlight
  .mag_relay_button = 1,  // For manually dropping magnet
  .encoder_A = 17,       // Reading encoder direction A
  .encoder_B = 18,       // Reading encoder direction B
  .microswitch = 15,     // Microswitch sensing arm in contact with electromagnet
  .arm_ext_sens = 3,         // Stepper pulse control
  .arm_ret_sens = 13,   // Stepper direction control NOW sens arm retract
  .arm_cmd_sign = 14      // Stepper enable
};


// Non blocking timing variables
unsigned long lastReadTime = 0;
unsigned long startTime = 0;

// Global variables for encoder
// --- Konfigurasjon: antall pulser per omdreining (counts per revolution) ---
const long CPR = 2048;  // juster etter din encoder
long totalPulses = 0;
double angleRad = 0;

// global_declarations.h

SemaphoreHandle_t extSenseSem = nullptr;
SemaphoreHandle_t retSenseSem = nullptr;

// Accelerometer with EMA filter parameters
Adafruit_MPU6050 mpu;
float filter_alpha = 0.05;                      // Alpha between 0 and 1. 1 Gives no filtering. alpha --> 0 gives maksimum filtering.
bool firstRead = true;                          // Flag for filter function 
float filteredAccelerometerValue = 0;               // Global filter verdi
float offsetZ = 0.0;                           // Calibration offset
bool isCalibrated = false;                     // Calibration flag
const int CALIB_SAMPLES = 100;                  // Calibration samples


// Obj for BME sensor
Adafruit_BME280 bme;

// LCD definitions
Adafruit_ST7735 tft = Adafruit_ST7735(&SPI, pin.CS_lcd, pin.TFT_DC, pin.TFT_RST);



// Parameter
const unsigned long data_collection_time = 6000;               // Datacollection time ms
const int step_length = 1;                          // Step length in ms for test, sample time

// Debounce-variabler
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;
bool lastButtonState = LOW;
bool buttonState = LOW;

unsigned long lastDebounceTime2 = 0;
unsigned long debounceDelay2 = 50;
bool lastButtonState2 = LOW;
bool buttonState2 = LOW;

