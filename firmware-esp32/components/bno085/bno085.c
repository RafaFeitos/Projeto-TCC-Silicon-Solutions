#include "bno085.h"

#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "sh2.h"
#include "sh2_SensorValue.h"
#include "sh2_err.h"

static const char TAG[] = "bno085";

static bno085_dev_t s_dev;
static sh2_Hal_t s_hal;
static i2c_master_bus_handle_t s_i2c_bus = NULL;
static i2c_master_dev_handle_t s_i2c_device = NULL;

static uint32_t s_accel_interval_us;
static uint32_t s_gyro_interval_us;
static bool s_accel_enabled;
static bool s_gyro_enabled;
static volatile bool s_need_reenable;

static bno085_acceleration_t s_last_acceleration;
static bno085_gyroscope_t s_last_gyroscope;
static volatile bool s_acceleration_updated;
static volatile bool s_gyroscope_updated;

/* Buffer usado pelo framing SHTP sobre I2C. */
static uint8_t s_i2c_rx_buf[SH2_HAL_MAX_TRANSFER_IN];

static int hal_open(sh2_Hal_t *self)
{
    (void)self;
    return 0;
}

static void hal_close(sh2_Hal_t *self)
{
    (void)self;
}

static int hal_read(sh2_Hal_t *self, uint8_t *pBuffer, unsigned len, uint32_t *t_us)
{
    (void)self;

    if (s_dev.int_gpio != GPIO_NUM_NC && gpio_get_level(s_dev.int_gpio) != 0) {
        return 0;
    }

    esp_err_t err = i2c_master_receive(
        s_i2c_device,
        s_i2c_rx_buf,
        4,
        100
    );
    if (err != ESP_OK) {
        ESP_LOGD(TAG, "falha lendo cabecalho: %s", esp_err_to_name(err));
        return 0;
    }

    uint16_t packet_size = (uint16_t)s_i2c_rx_buf[0] |
                           ((uint16_t)s_i2c_rx_buf[1] << 8);
    packet_size &= (uint16_t)~0x8000U;

    if (packet_size == 0 || packet_size > len || packet_size > sizeof(s_i2c_rx_buf)) {
        ESP_LOGD(TAG, "packet_size invalido: %u", packet_size);
        return 0;
    }

    /* O BNO08x reinicia a leitura do pacote no segundo acesso I2C; por isso
     * lemos novamente o pacote completo, incluindo o cabecalho SHTP. */
    err = i2c_master_receive(
        s_i2c_device,
        s_i2c_rx_buf,
        packet_size,
        100
    );
    if (err != ESP_OK) {
        ESP_LOGD(TAG, "falha lendo pacote: %s", esp_err_to_name(err));
        return 0;
    }

    memcpy(pBuffer, s_i2c_rx_buf, packet_size);
    if (t_us != NULL) {
        *t_us = (uint32_t)esp_timer_get_time();
    }

    return (int)packet_size;
}

static int hal_write(sh2_Hal_t *self, uint8_t *pBuffer, unsigned len)
{
    (void)self;

    const esp_err_t err = i2c_master_transmit(
        s_i2c_device,
        pBuffer,
        len,
        100
    );

    return (err == ESP_OK) ? (int)len : 0;
}

static uint32_t hal_get_time_us(sh2_Hal_t *self)
{
    (void)self;
    return (uint32_t)esp_timer_get_time();
}

static void event_callback(void *cookie, sh2_AsyncEvent_t *event)
{
    (void)cookie;

    if (event->eventId == SH2_RESET) {
        ESP_LOGW(TAG, "BNO085 resetou; reabilitando relatorio ativo");
        s_need_reenable = true;
    }
}

static void sensor_callback(void *cookie, sh2_SensorEvent_t *event)
{
    (void)cookie;
    sh2_SensorValue_t value;
    if (sh2_decodeSensorEvent(&value, event) != SH2_OK) return;

    if (value.sensorId == SH2_ACCELEROMETER) {
        s_last_acceleration.x = value.un.accelerometer.x;
        s_last_acceleration.y = value.un.accelerometer.y;
        s_last_acceleration.z = value.un.accelerometer.z;
        s_last_acceleration.timestamp_us = value.timestamp;
        s_last_acceleration.valid = true;
        s_acceleration_updated = true;
    }
    else if (value.sensorId == SH2_GYROSCOPE_CALIBRATED) {
        s_last_gyroscope.x = value.un.gyroscope.x;
        s_last_gyroscope.y = value.un.gyroscope.y;
        s_last_gyroscope.z = value.un.gyroscope.z;
        s_last_gyroscope.timestamp_us = value.timestamp;
        s_last_gyroscope.valid = true;
        s_gyroscope_updated = true;
    }
}

static esp_err_t init_i2c_bus(void)
{
    if (s_i2c_bus == NULL) {
        const i2c_master_bus_config_t bus_config = {
            .i2c_port = s_dev.i2c_port,
            .sda_io_num = s_dev.sda_gpio,
            .scl_io_num = s_dev.scl_gpio,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .intr_priority = 0,
            .trans_queue_depth = 0,
            .flags = {
                .enable_internal_pullup = true,
                .allow_pd = false,
            },
        };

        esp_err_t err = i2c_new_master_bus(&bus_config, &s_i2c_bus);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "falha criando barramento I2C: %s", esp_err_to_name(err));
            return err;
        }
    }

    if (s_i2c_device == NULL) {
        const i2c_device_config_t dev_config = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address = s_dev.i2c_addr,
            .scl_speed_hz = 400000,
            .scl_wait_us = 0,
            .flags = {
                .disable_ack_check = false,
            },
        };

        esp_err_t err = i2c_master_bus_add_device(
            s_i2c_bus,
            &dev_config,
            &s_i2c_device
        );
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "falha adicionando BNO085 ao I2C: %s", esp_err_to_name(err));
            return err;
        }
    }

    return ESP_OK;
}

esp_err_t bno085_init(const bno085_dev_t *dev)
{
    if (dev == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    s_dev = *dev;
    memset(&s_last_acceleration, 0, sizeof(s_last_acceleration));
    memset(&s_last_gyroscope, 0, sizeof(s_last_gyroscope));
    s_acceleration_updated = false;
    s_gyroscope_updated = false;
    s_accel_enabled = false;
    s_gyro_enabled = false;
    s_accel_interval_us = 0;
    s_gyro_interval_us = 0;
    s_need_reenable = false;

    esp_err_t err = init_i2c_bus();
    if (err != ESP_OK) {
        return err;
    }

    if (s_dev.reset_gpio != GPIO_NUM_NC) {
        const gpio_config_t reset_cfg = {
            .pin_bit_mask = 1ULL << s_dev.reset_gpio,
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        ESP_ERROR_CHECK(gpio_config(&reset_cfg));
    }

    if (s_dev.int_gpio != GPIO_NUM_NC) {
        const gpio_config_t int_cfg = {
            .pin_bit_mask = 1ULL << s_dev.int_gpio,
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        ESP_ERROR_CHECK(gpio_config(&int_cfg));
    }

    if (s_dev.reset_gpio != GPIO_NUM_NC) {
        gpio_set_level(s_dev.reset_gpio, 0);
        vTaskDelay(pdMS_TO_TICKS(10));
        gpio_set_level(s_dev.reset_gpio, 1);
        vTaskDelay(pdMS_TO_TICKS(20));
    }

    if (s_dev.int_gpio != GPIO_NUM_NC) {
        const TickType_t timeout_ticks = pdMS_TO_TICKS(1000);
        const TickType_t start_tick = xTaskGetTickCount();

        while ((xTaskGetTickCount() - start_tick) < timeout_ticks) {
            if (gpio_get_level(s_dev.int_gpio) == 0) {
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(5));
        }

        if (gpio_get_level(s_dev.int_gpio) != 0) {
            ESP_LOGE(TAG, "BNO085 nao assertou INT apos reset");
            return ESP_ERR_TIMEOUT;
        }
    }

    s_hal.open = hal_open;
    s_hal.close = hal_close;
    s_hal.read = hal_read;
    s_hal.write = hal_write;
    s_hal.getTimeUs = hal_get_time_us;

    const int status = sh2_open(&s_hal, event_callback, NULL);
    if (status != SH2_OK) {
        ESP_LOGE(TAG, "sh2_open falhou: %d", status);
        return ESP_FAIL;
    }

    sh2_setSensorCallback(sensor_callback, NULL);
    s_need_reenable = false;

    ESP_LOGI(
        TAG,
        "BNO085 inicializado: I2C%d SDA=%d SCL=%d addr=0x%02X",
        (int)s_dev.i2c_port,
        (int)s_dev.sda_gpio,
        (int)s_dev.scl_gpio,
        s_dev.i2c_addr
    );

    return ESP_OK;
}

static esp_err_t enable_sensor(sh2_SensorId_t sensor_id, uint32_t interval_us)
{
    sh2_SensorConfig_t config = {0};
    config.reportInterval_us = interval_us;
    const int status = sh2_setSensorConfig(sensor_id, &config);
    if (status != SH2_OK) {
        ESP_LOGE(TAG, "sh2_setSensorConfig(0x%02X) falhou: %d", sensor_id, status);
        return ESP_FAIL;
    }
    return ESP_OK;
}

esp_err_t bno085_enable_accelerometer(uint32_t interval_us)
{
    s_acceleration_updated = false;
    esp_err_t err = enable_sensor(SH2_ACCELEROMETER, interval_us);
    if (err == ESP_OK) { s_accel_enabled = true; s_accel_interval_us = interval_us; }
    return err;
}

esp_err_t bno085_enable_gyroscope(uint32_t interval_us)
{
    s_gyroscope_updated = false;
    esp_err_t err = enable_sensor(SH2_GYROSCOPE_CALIBRATED, interval_us);
    if (err == ESP_OK) { s_gyro_enabled = true; s_gyro_interval_us = interval_us; }
    return err;
}

void bno085_service(void)
{
    sh2_service();
    if (!s_need_reenable) return;
    bool ok = true;
    if (s_accel_enabled && enable_sensor(SH2_ACCELEROMETER, s_accel_interval_us) != ESP_OK) ok = false;
    if (s_gyro_enabled && enable_sensor(SH2_GYROSCOPE_CALIBRATED, s_gyro_interval_us) != ESP_OK) ok = false;
    if (ok) s_need_reenable = false;
}

bool bno085_get_accelerometer(bno085_acceleration_t *out)
{
    if (!out || !s_last_acceleration.valid || !s_acceleration_updated) return false;
    *out = s_last_acceleration; s_acceleration_updated = false; return true;
}

bool bno085_get_gyroscope(bno085_gyroscope_t *out)
{
    if (!out || !s_last_gyroscope.valid || !s_gyroscope_updated) return false;
    *out = s_last_gyroscope; s_gyroscope_updated = false; return true;
}

bool bno085_get_accel_gyro_sample(bno085_accel_gyro_sample_t *out)
{
    if (!out || !s_acceleration_updated || !s_gyroscope_updated ||
        !s_last_acceleration.valid || !s_last_gyroscope.valid) return false;
    out->accel_x=s_last_acceleration.x; out->accel_y=s_last_acceleration.y; out->accel_z=s_last_acceleration.z;
    out->gyro_x=s_last_gyroscope.x; out->gyro_y=s_last_gyroscope.y; out->gyro_z=s_last_gyroscope.z;
    out->timestamp_us = (s_last_acceleration.timestamp_us > s_last_gyroscope.timestamp_us) ? s_last_acceleration.timestamp_us : s_last_gyroscope.timestamp_us;
    s_acceleration_updated=false; s_gyroscope_updated=false; return true;
}
