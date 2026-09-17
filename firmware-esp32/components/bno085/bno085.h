#ifndef __BNO085_H__
#define __BNO085_H__
#include <stdbool.h>
#include <stdint.h>
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_err.h"
#ifdef __cplusplus
extern "C" {
#endif
#define BNO085_I2C_ADDR_DEFAULT 0x4A
#define BNO085_I2C_ADDR_ALT 0x4B
typedef struct { i2c_port_num_t i2c_port; gpio_num_t sda_gpio; gpio_num_t scl_gpio; uint8_t i2c_addr; gpio_num_t reset_gpio; gpio_num_t int_gpio; } bno085_dev_t;
typedef struct { float x,y,z; uint64_t timestamp_us; bool valid; } bno085_acceleration_t;
typedef struct { float x,y,z; uint64_t timestamp_us; bool valid; } bno085_gyroscope_t;
typedef struct { float accel_x,accel_y,accel_z; float gyro_x,gyro_y,gyro_z; uint64_t timestamp_us; } bno085_accel_gyro_sample_t;
esp_err_t bno085_init(const bno085_dev_t *dev);
esp_err_t bno085_enable_accelerometer(uint32_t interval_us);
esp_err_t bno085_enable_gyroscope(uint32_t interval_us);
void bno085_service(void);
bool bno085_get_accelerometer(bno085_acceleration_t *out);
bool bno085_get_gyroscope(bno085_gyroscope_t *out);
bool bno085_get_accel_gyro_sample(bno085_accel_gyro_sample_t *out);
#ifdef __cplusplus
}
#endif
#endif
