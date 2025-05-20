/* =============================================================================
                               Hammer node Main
   ============================================================================= */

// Custom libraries for storing functions and global declarations
#include <global_declarations.h>
#include <communications.h>
#include <Arduino.h>

// Declare task loops for initialization in setup()
void loop_core_0(void *parameter);
void loop_core_1(void *parameter);

// ISR‐rutikker
// Debounce‐tidsstempler (i millisekunder)
volatile uint32_t lastExtMs = 0;
volatile uint32_t lastRetMs = 0;

// ISR for utstrakt arm
void IRAM_ATTR onArmExtended() {
  uint32_t now = xTaskGetTickCountFromISR() * portTICK_PERIOD_MS;
  if (now - lastExtMs < 50)   // ignorer nye kanter innen 50 ms
    return;
  lastExtMs = now;

  BaseType_t woken = pdFALSE;
  xSemaphoreGiveFromISR(extSenseSem, &woken);
  if (woken) portYIELD_FROM_ISR();
}

// ISR for tilbaketrukket arm
void IRAM_ATTR onArmRetracted() {
  uint32_t now = xTaskGetTickCountFromISR() * portTICK_PERIOD_MS;
  if (now - lastRetMs < 50)   // ignorer nye kanter innen 50 ms
    return;
  lastRetMs = now;

  BaseType_t woken = pdFALSE;
  xSemaphoreGiveFromISR(retSenseSem, &woken);
  if (woken) portYIELD_FROM_ISR();
}



void setup()
{
  Serial.begin(115200);

  // Opprett semaforene
  extSenseSem = xSemaphoreCreateBinary();
  configASSERT(extSenseSem != nullptr);
  retSenseSem = xSemaphoreCreateBinary();
  configASSERT(retSenseSem != nullptr);

  // Initialise pins
  pinMode(pin.test_button, INPUT_PULLUP);      // Bruker intern pullup for knappen
  pinMode(pin.mag_relay_button, INPUT_PULLUP); // Bruker intern pullup for knappen
  pinMode(pin.relay, OUTPUT);
  pinMode(pin.lcd_backlight, OUTPUT);
  pinMode(pin.encoder_A, INPUT_PULLUP);
  pinMode(pin.encoder_B, INPUT_PULLUP);
  pinMode(pin.arm_ext_sens, INPUT_PULLUP);
  pinMode(pin.arm_ret_sens, INPUT);
  pinMode(pin.arm_cmd_sign, OUTPUT);

  // Interrupts
  attachInterrupt(digitalPinToInterrupt(pin.arm_ext_sens),
                  onArmExtended, FALLING); // FALLING siden vi bruker pull-up
  attachInterrupt(digitalPinToInterrupt(pin.arm_ret_sens),
                  onArmRetracted, FALLING);

  ///   ENCODER PCNT
  // Bygg konfigurasjonsstrukturen felt for felt:
  pcnt_config_t pcnt_cfg;
  pcnt_cfg.pulse_gpio_num = pin.encoder_A; // A
  pcnt_cfg.ctrl_gpio_num = pin.encoder_B;  // B
  pcnt_cfg.channel = PCNT_CHANNEL;         // channel 0
  pcnt_cfg.unit = PCNT_UNIT;               // unit 0
  pcnt_cfg.pos_mode = PCNT_COUNT_INC;      // stigende A = +1
  pcnt_cfg.neg_mode = PCNT_COUNT_DEC;      // fallende A = –1
  pcnt_cfg.lctrl_mode = PCNT_MODE_KEEP;    // når B=LOW: behold retning
  pcnt_cfg.hctrl_mode = PCNT_MODE_REVERSE; // når B=HIGH: reverser retning
  pcnt_cfg.counter_h_lim = PCNT_H_LIM_VAL; // maks‑grense (ikke kritisk her)
  pcnt_cfg.counter_l_lim = PCNT_L_LIM_VAL; // min‑grense

  // Konfigurer og start PCNT‑unit:
  pcnt_unit_config(&pcnt_cfg);
  //pcnt_set_filter_value(PCNT_UNIT, PCNT_FILTER_US);
  //pcnt_filter_enable(PCNT_UNIT);
  pcnt_filter_disable(PCNT_UNIT);
  pcnt_counter_pause(PCNT_UNIT);
  pcnt_counter_clear(PCNT_UNIT);
  pcnt_counter_resume(PCNT_UNIT);
  // ENCODER PCNT slutt

  /*
  Wire.begin(pin.SDA, pin.SCL);
  if (!mpu.begin())
  {
    Serial.println("MPU initialisering feilet!");
    tft.fillScreen(ST77XX_BLACK);
    tft.setCursor(0, 0);
    tft.setTextSize(1);
    tft.println("MPU initialisering feilet!");
    while (1)
      ;
  }
  */

  // Starter I2C for BME
  Wire.begin(pin.SDA, pin.SCL); 
  bool status = bme.begin(0x76);  // vanligvis 0x76, eventuelt 0x77 avhengig av modul

  setup_lcd();
  //setup_wifi();
  // setup_MQTT();
  system_reset();

  // Creating multi-core tasking
  xTaskCreatePinnedToCore(
      loop_core_0,      // Task function
      "Communications", // Task name
      10000,            // Stack-size
      NULL,             // Parameters
      1,                // Priority
      NULL,             // Task handle
      0                 // Core number
  );

  xTaskCreatePinnedToCore(
      loop_core_1,         // Task function
      "System Operations", // Task name
      10000,               // Stack-size
      NULL,                // Parameters
      1,                   // Priority
      NULL,                // Task handle
      1                    // Core number
  );
}

/* ------------- LOOP START ----------------*/

void loop_core_0(void *parameter)
{

  while (true)
  {
    if (!client.connected())
    {
      // reconnect();      AKTIVER FOR MQTT
      vTaskDelay(500 / portTICK_PERIOD_MS);
    }
    else
    {
      // client.loop();    AKTIVER FOR MQTT
    }

    handleSerialCommands(); // Listening for serial commands
    vTaskDelay(10);         // Small delay in loop to not use 100% CPU
  }
}

void loop_core_1(void *parameter)
{
  while (true)
  {

    // Updating IOs
    check_button();

    // Starting test program
    if (testStart == true)
    {
      run_test();
    }

    if (magDrop == true)
    {
      digitalWrite(pin.relay, HIGH);
      vTaskDelay(pdMS_TO_TICKS(500));
      digitalWrite(pin.relay, LOW);
      magDrop = false;
    }
    vTaskDelay(10);
  }
}

void loop()
{
  // The default loop() is empty because we use FreeRTOS tasks instead.
}
