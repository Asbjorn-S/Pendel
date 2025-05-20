/* =============================================================================
                           Hammer node functions header                              
   ============================================================================= */


#ifndef FUNCTIONS_LIBRARY_H
#define FUNCTIONS_LIBRARY_H

#include <global_declarations.h>
#include <communications.h>


// Button check with debounce
void check_button();

// Run test
void run_test();

// Data from encoder
double readEncoderAngle();

// Fetch measurement data and store it in a JSON object
void get_data(JsonDocument &data);

// Reset the system after a test
void system_reset();

// Calibrate accelerometer
void calibrateOffset();


// Function for controlling stepper motor raising arm
void raise_arm();


// Publish a JSON object to MQTT
void publish_json(JsonDocument &data);

void onMqttPublishCallback(bool success);



// Set up LCD
void setup_lcd();


#endif // FUNCTIONS_LIBRARY_H