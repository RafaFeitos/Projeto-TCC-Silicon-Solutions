#include "imu_config.h"

#include "esp_err.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "bno085.h"

static const char *TAG = "imu_config";
static TaskHandle_t imu_task_handle = NULL;
static uint32_t s_sample_interval_us = 10000;

QueueHandle_t imu_queue = NULL;

static void imu_task_code(void *pvParameter)
{
    (void)pvParameter;

    /* O service loop roda mais rapido que o report interval. O driver so
     * libera uma amostra quando um NOVO evento SH-2 de acelerometro chega. */
    TickType_t service_period = pdMS_TO_TICKS(2);
    if (service_period == 0) {
        service_period = 1;
    }
    TickType_t last_wake_tick = xTaskGetTickCount();

    while (1) {
        bno085_service();

        bno085_accel_gyro_sample_t sensor;
        if (bno085_get_accel_gyro_sample(&sensor)) {
            const imu_sample_t sample = {
                .accel_x = sensor.accel_x, .accel_y = sensor.accel_y, .accel_z = sensor.accel_z,
                .gyro_x = sensor.gyro_x, .gyro_y = sensor.gyro_y, .gyro_z = sensor.gyro_z,
                .timestamp_us = sensor.timestamp_us,
            };

            if (xQueueSend(imu_queue, &sample, 0) != pdPASS) {
                ESP_LOGW(TAG, "Fila IMU cheia; amostra descartada");
            }
        }

        vTaskDelayUntil(&last_wake_tick, service_period);
    }
}

esp_err_t imu_config_init(uint32_t sample_interval_us)
{
    if (sample_interval_us == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    s_sample_interval_us = sample_interval_us;

    ESP_LOGI(
        TAG,
        "Inicializando BNO085: intervalo=%lu us (%.2f Hz)",
        (unsigned long)s_sample_interval_us,
        1000000.0f / (float)s_sample_interval_us
    );

    const bno085_dev_t dev = {
        .i2c_port = (i2c_port_num_t)CONFIG_BNO085_I2C_PORT,
        .sda_gpio = (gpio_num_t)CONFIG_BNO085_SDA_GPIO,
        .scl_gpio = (gpio_num_t)CONFIG_BNO085_SCL_GPIO,
        .i2c_addr = CONFIG_BNO085_I2C_ADDR,
        .reset_gpio = (gpio_num_t)CONFIG_BNO085_RESET_GPIO,
        .int_gpio = (gpio_num_t)CONFIG_BNO085_INT_GPIO,
    };

    const int max_attempts = 3;
    esp_err_t err = ESP_FAIL;

    for (int attempt = 1; attempt <= max_attempts; attempt++) {
        err = bno085_init(&dev);
        if (err == ESP_OK) {
            break;
        }

        ESP_LOGW(
            TAG,
            "Tentativa %d/%d de inicializacao falhou: %s",
            attempt,
            max_attempts,
            esp_err_to_name(err)
        );

        if (attempt < max_attempts) {
            vTaskDelay(pdMS_TO_TICKS(500));
        }
    }

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Nao foi possivel inicializar o BNO085");
        return err;
    }

    err = bno085_enable_accelerometer(s_sample_interval_us);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Falha ao habilitar acelerometro: %s", esp_err_to_name(err));
        return err;
    }

    err = bno085_enable_gyroscope(s_sample_interval_us);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Falha ao habilitar giroscopio: %s", esp_err_to_name(err));
        return err;
    }

    imu_queue = xQueueCreate(64, sizeof(imu_sample_t));
    if (imu_queue == NULL) {
        ESP_LOGE(TAG, "Falha ao criar fila da IMU");
        return ESP_ERR_NO_MEM;
    }

    const BaseType_t task_ok = xTaskCreate(
        imu_task_code,
        "imu_task",
        5 * 1024,
        NULL,
        5,
        &imu_task_handle
    );

    if (task_ok != pdPASS) {
        vQueueDelete(imu_queue);
        imu_queue = NULL;
        ESP_LOGE(TAG, "Falha ao criar task da IMU");
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "BNO085 pronto: acelerometro + giroscopio");
    return ESP_OK;
}
