#include "esp_camera.h"
#include <HardwareSerial.h>

// Select camera model (AI-Thinker is most common)
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// Calibration parameters for movement scaling
const int SCREEN_WIDTH = 1280;
const int SCREEN_HEIGHT = 720;
const int PINCH_THRESHOLD = 20;  // Pixel distance between fingers to trigger click

void setup() {
  Serial.begin(115200);  // Wired serial connection to laptop

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size = FRAMESIZE_QVGA;  // 320x240 for faster on-device processing
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
}

void loop() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    return;
  }

  long color_x_sum = 0;
  long color_y_sum = 0;
  int pixel_count = 0;

  // Iterate through the RGB565 frame buffer (2 bytes per pixel)
  for (int i = 0; i < fb->len; i += 2) {
    uint8_t low_byte = fb->buf[i];
    uint8_t high_byte = fb->buf[i+1];
    
    // Extract 8-bit RGB channels from the 16-bit RGB565 format
    uint8_t r = (high_byte & 0xF8);
    uint8_t g = ((high_byte & 0x07) << 5) | ((low_byte & 0xE0) >> 3);
    uint8_t b = ((low_byte & 0x1F) << 3);
    
    // Color thresholding: Adjust these values to isolate a brightly colored marker (e.g., Red)
    if (r > 150 && g < 70 && b < 70) {
      int pixel_index = i / 2;
      int px = pixel_index % 320; // 320 is the QVGA frame width
      int py = pixel_index / 320;
      
      color_x_sum += px;
      color_y_sum += py;
      pixel_count++;
    }
  }

  // Default to center if the tracking color is not visible
  int raw_x = 160; 
  int raw_y = 120;
  
  // If the color is found, calculate the center point (centroid)
  if (pixel_count > 5) { // Minimum pixel area threshold to ignore noise
    raw_x = color_x_sum / pixel_count;
    raw_y = color_y_sum / pixel_count;
  }

  // TODO: Add logic for a second color marker to calculate pinch distance for clicking
  bool is_pinched = false; 

  // Absolute position mapping to screen coordinates
  // Note: We invert the X-axis so the cursor mirrors your hand movement intuitively
  int cursor_x = map(raw_x, 320, 0, 0, SCREEN_WIDTH);
  int cursor_y = map(raw_y, 0, 240, 0, SCREEN_HEIGHT);

  // Send only cursor movement updates and mouse-button events to the laptop
  Serial.printf("%d,%d,%d\n", cursor_x, cursor_y, is_pinched ? 1 : 0);

  esp_camera_fb_return(fb);
  delay(16);
}