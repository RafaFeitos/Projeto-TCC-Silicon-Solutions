#ifndef __IMU_CONFIG_H__
#define __IMU_CONFIG_H__
#ifdef __cplusplus
extern "C" {
#endif
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
typedef struct { float accel_x,accel_y,accel_z; float gyro_x,gyro_y,gyro_z; uint64_t timestamp_us; } imu_sample_t;
extern QueueHandle_t imu_queue;
esp_err_t imu_config_init(uint32_t sample_interval_us);
#ifdef __cplusplus
}
#endif
#endif
