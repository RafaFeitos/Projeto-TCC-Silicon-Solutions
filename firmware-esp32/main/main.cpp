#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <inttypes.h>

#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_adc/adc_oneshot.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "edge-impulse-sdk/classifier/ei_run_classifier.h"
#include "imu_config.h"
#include "mqtt_manager.h"

/* ======================== Edge Impulse ======================== */

static_assert(
    EI_CLASSIFIER_RAW_SAMPLES_PER_FRAME == 6,
    "Este firmware espera accX,accY,accZ,gyrX,gyrY,gyrZ"
);

static_assert(
    (EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE % EI_CLASSIFIER_RAW_SAMPLES_PER_FRAME) == 0,
    "Frame do modelo precisa ser multiplo do numero de eixos"
);

static float features[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE] = {0};

/* ======================== E18 / RPM =========================== */
/*
 * Objeto medido: disco/circulo simetrico com 4 furos.
 * Cada furo deve produzir 1 borda de descida no E18-D80NK.
 */
#define E18_GPIO                    GPIO_NUM_3
#define RPM_PULSES_PER_REV          4U
#define RPM_WINDOW_MS               1000U
#define E18_MIN_PULSE_INTERVAL_US   500LL

static portMUX_TYPE s_pulse_mux = portMUX_INITIALIZER_UNLOCKED;
static volatile uint32_t s_pulse_count = 0;
static volatile int64_t s_last_pulse_us = 0;

static int64_t s_rpm_window_start_us = 0;
static float s_rpm_raw = 0.0f;
static float s_rpm_filtered = 0.0f;
static float s_pulse_hz = 0.0f;
static uint32_t s_last_pulses = 0;
static bool s_first_rpm = true;

/* ======================== NTC / Temperatura =================== */
/*
 * NTC 10K MF52:
 *
 * 3V3
 *  |
 * [5,1k]
 *  |
 *  +---- GPIO2 / ADC1_CHANNEL_1
 *  |
 * [NTC 10k]
 *  |
 * GND
 */
#define NTC_ADC_UNIT            ADC_UNIT_1
#define NTC_ADC_CHANNEL         ADC_CHANNEL_1
#define FIXED_RESISTOR_OHM      5100.0f
#define NTC_NOMINAL_OHM         10000.0f
#define NTC_BETA                3950.0f
#define NOMINAL_TEMP_C          25.0f

static adc_oneshot_unit_handle_t s_adc_handle = nullptr;
static float s_temperature_c = 0.0f;
static int s_ntc_raw = 0;
static float s_ntc_voltage = 0.0f;
static float s_ntc_resistance = 0.0f;

/* ======================== Edge Impulse helpers ================ */

static int raw_feature_get_data(size_t offset, size_t length, float *out_ptr)
{
    if (offset + length > EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
        return -1;
    }

    memcpy(out_ptr, features + offset, length * sizeof(float));
    return 0;
}

/* ======================== RPM ================================= */

static void IRAM_ATTR e18_isr_handler(void *arg)
{
    (void)arg;

    const int64_t now_us = esp_timer_get_time();
    const int64_t last_us = s_last_pulse_us;

    if ((last_us == 0) || ((now_us - last_us) >= E18_MIN_PULSE_INTERVAL_US)) {
        portENTER_CRITICAL_ISR(&s_pulse_mux);
        s_pulse_count++;
        s_last_pulse_us = now_us;
        portEXIT_CRITICAL_ISR(&s_pulse_mux);
    }
}

static esp_err_t configure_e18_rpm(void)
{
    gpio_config_t cfg = {};
    cfg.pin_bit_mask = 1ULL << E18_GPIO;
    cfg.mode = GPIO_MODE_INPUT;
    cfg.pull_up_en = GPIO_PULLUP_DISABLE;
    cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
    cfg.intr_type = GPIO_INTR_NEGEDGE;

    esp_err_t err = gpio_config(&cfg);
    if (err != ESP_OK) {
        return err;
    }

    err = gpio_install_isr_service(0);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }

    err = gpio_isr_handler_add(E18_GPIO, e18_isr_handler, nullptr);
    if (err != ESP_OK) {
        return err;
    }

    s_rpm_window_start_us = esp_timer_get_time();

    ESP_LOGI("RPM", "E18-D80NK GPIO%d, borda de descida", E18_GPIO);
    ESP_LOGI("RPM", "Disco com %u furos = %u pulsos/volta",
             RPM_PULSES_PER_REV, RPM_PULSES_PER_REV);

    return ESP_OK;
}

static void update_rpm_if_due(void)
{
    const int64_t now_us = esp_timer_get_time();
    const int64_t elapsed_us = now_us - s_rpm_window_start_us;

    if (elapsed_us < ((int64_t)RPM_WINDOW_MS * 1000LL)) {
        return;
    }

    uint32_t pulses;

    portENTER_CRITICAL(&s_pulse_mux);
    pulses = s_pulse_count;
    s_pulse_count = 0;
    portEXIT_CRITICAL(&s_pulse_mux);

    s_pulse_hz = ((float)pulses * 1000000.0f) / (float)elapsed_us;

    /*
     * 4 furos => 4 pulsos por volta:
     * RPM = frequencia_de_pulsos * 60 / 4
     */
    s_rpm_raw = (s_pulse_hz * 60.0f) / (float)RPM_PULSES_PER_REV;

    if (s_first_rpm) {
        s_rpm_filtered = s_rpm_raw;
        s_first_rpm = false;
    }
    else {
        /* Mesma suavizacao do teste validado. */
        s_rpm_filtered = (0.70f * s_rpm_filtered) + (0.30f * s_rpm_raw);
    }

    s_last_pulses = pulses;
    s_rpm_window_start_us = now_us;
}

/* ======================== NTC ================================= */

static float calculate_ntc_resistance(float voltage)
{
    const float vin = 3.3f;

    if (voltage <= 0.001f) {
        return 0.0f;
    }

    if (voltage >= (vin - 0.001f)) {
        return 999999.0f;
    }

    return FIXED_RESISTOR_OHM * voltage / (vin - voltage);
}

static float calculate_temperature_c(float resistance)
{
    if (resistance <= 0.0f) {
        return -273.15f;
    }

    const float t0_kelvin = NOMINAL_TEMP_C + 273.15f;

    const float inv_t =
        (1.0f / t0_kelvin) +
        (1.0f / NTC_BETA) * logf(resistance / NTC_NOMINAL_OHM);

    return (1.0f / inv_t) - 273.15f;
}

static esp_err_t configure_ntc(void)
{
    adc_oneshot_unit_init_cfg_t init_config = {};
    init_config.unit_id = NTC_ADC_UNIT;

    esp_err_t err = adc_oneshot_new_unit(&init_config, &s_adc_handle);
    if (err != ESP_OK) {
        return err;
    }

    adc_oneshot_chan_cfg_t channel_config = {};
    channel_config.atten = ADC_ATTEN_DB_12;
    channel_config.bitwidth = ADC_BITWIDTH_DEFAULT;

    err = adc_oneshot_config_channel(
        s_adc_handle,
        NTC_ADC_CHANNEL,
        &channel_config
    );

    if (err == ESP_OK) {
        ESP_LOGI("NTC", "NTC 10K MF52 em GPIO2 / ADC1_CHANNEL_1");
        ESP_LOGI("NTC", "Rfixo=5.1kOhm, Beta=%.0f", NTC_BETA);
    }

    return err;
}

static esp_err_t read_temperature(void)
{
    int raw = 0;
    const esp_err_t err =
        adc_oneshot_read(s_adc_handle, NTC_ADC_CHANNEL, &raw);

    if (err != ESP_OK) {
        return err;
    }

    s_ntc_raw = raw;
    s_ntc_voltage = ((float)raw / 4095.0f) * 3.3f;
    s_ntc_resistance = calculate_ntc_resistance(s_ntc_voltage);
    s_temperature_c = calculate_temperature_c(s_ntc_resistance);

    return ESP_OK;
}


/* ======================== Protocolo serial ==================== */
/*
 * Contrato consumido pelo backend/app/services/serial_ingest.py:
 *
 * @M,projeto,versao,amostras,eixos,intervalo_ms
 * @S,timestamp_us,accel_x,accel_y,accel_z
 * @R,timestamp_us,rpm_raw,rpm_filtrado,pulsos,frequencia_hz
 * @T,timestamp_us,temperatura_c,ntc_raw,tensao,resistencia
 * @I,timestamp_us,classe,confianca,versao
 *
 * O modelo usa 6 eixos (acelerometro + giroscopio), mas @S envia somente
 * aceleracao XYZ porque o backend usa essas amostras para sinal/RMS.
 */

static void serial_protocol_metadata(void)
{
    ei_printf(
        "@M,%s,%d,%d,%d,%d\n",
        EI_CLASSIFIER_PROJECT_NAME,
        EI_CLASSIFIER_PROJECT_DEPLOY_VERSION,
        EI_CLASSIFIER_RAW_SAMPLE_COUNT,
        EI_CLASSIFIER_RAW_SAMPLES_PER_FRAME,
        EI_CLASSIFIER_INTERVAL_MS
    );
}

static void serial_protocol_sample(const imu_sample_t &sample)
{
    ei_printf(
        "@S,%" PRIu64 ",%.6f,%.6f,%.6f\n",
        sample.timestamp_us,
        sample.accel_x,
        sample.accel_y,
        sample.accel_z
    );
}

static void serial_protocol_telemetry_and_inference(
    const ei_impulse_result_t &result,
    uint16_t best_index,
    float best_value
)
{
    const int64_t timestamp_us = esp_timer_get_time();

    ei_printf(
        "@R,%" PRId64 ",%.3f,%.3f,%" PRIu32 ",%.3f\n",
        timestamp_us,
        s_rpm_raw,
        s_rpm_filtered,
        s_last_pulses,
        s_pulse_hz
    );

    ei_printf(
        "@T,%" PRId64 ",%.3f,%d,%.6f,%.3f\n",
        timestamp_us,
        s_temperature_c,
        s_ntc_raw,
        s_ntc_voltage,
        s_ntc_resistance
    );

    /*
     * @I deve ser a ultima linha da janela. Ao recebe-la, o backend fecha
     * a janela de amostras, associa RPM/temperatura e publica no dashboard.
     * A confianca e enviada em 0..1, como o parser do backend espera.
     */
    ei_printf(
        "@I,%" PRId64 ",%s,%.6f,%d\n",
        timestamp_us,
        result.classification[best_index].label,
        best_value,
        EI_CLASSIFIER_PROJECT_DEPLOY_VERSION
    );
}

/* ======================== Saida =============================== */

static void print_classifier_result(const ei_impulse_result_t &result)
{
    uint16_t best_index = 0;
    float best_value = 0.0f;

    ei_printf("Predicoes:\n");

    for (uint16_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
        const float value = result.classification[i].value;

        ei_printf(
            "  %s: %.2f%%\n",
            result.classification[i].label,
            value * 100.0f
        );

        if (value > best_value) {
            best_value = value;
            best_index = i;
        }
    }

    serial_protocol_telemetry_and_inference(
        result,
        best_index,
        best_value
    );

    ei_printf(
        "Resultado: %s (%.2f%%)\n",
        result.classification[best_index].label,
        best_value * 100.0f
    );

    ei_printf(
        "RPM: %.1f | RPM filtrado: %.1f | pulsos: %" PRIu32
        " | freq: %.1f Hz | 4 furos/volta\n",
        s_rpm_raw,
        s_rpm_filtered,
        s_last_pulses,
        s_pulse_hz
    );

    ei_printf(
        "Temperatura: %.2f C | NTC raw: %d | V: %.3f V | R: %.1f ohm\n",
        s_temperature_c,
        s_ntc_raw,
        s_ntc_voltage,
        s_ntc_resistance
    );

    ei_printf(
        "Timing: DSP %d ms | classificacao %d ms | anomalia %d ms\n\n",
        result.timing.dsp,
        result.timing.classification,
        result.timing.anomaly
    );

    char json[768];
    int n = snprintf(json, sizeof(json),
        "{\"classificacao\":\"%s\",\"confianca\":%.4f,\"rpm\":%.1f,\"temperatura_c\":%.2f,\"probabilidades\":{",
        result.classification[best_index].label, best_value, s_rpm_filtered, s_temperature_c);
    for (uint16_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT && n > 0 && n < (int)sizeof(json); i++) {
        n += snprintf(json + n, sizeof(json) - n, "%s\"%s\":%.4f",
            (i == 0 ? "" : ","), result.classification[i].label, result.classification[i].value);
    }
    if (n > 0 && n < (int)sizeof(json) - 3) {
        snprintf(json + n, sizeof(json) - n, "}}");
        mqtt_manager_publish(json);
    }
}

/* ======================== Aplicacao =========================== */

extern "C" void app_main(void)
{
    ei_printf("\nIndustrial Monitor - BNO085 + Edge Impulse + RPM + Temperatura\n");
    ei_printf("Modelo: %s\n", EI_CLASSIFIER_PROJECT_NAME);
    ei_printf(
        "Entrada IA: %d amostras x %d eixos | intervalo %d ms | frame %d floats\n",
        EI_CLASSIFIER_RAW_SAMPLE_COUNT,
        EI_CLASSIFIER_RAW_SAMPLES_PER_FRAME,
        EI_CLASSIFIER_INTERVAL_MS,
        EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE
    );

    const esp_err_t mqtt_err = mqtt_manager_start();
    if (mqtt_err != ESP_OK) {
        ei_printf("MQTT/Wi-Fi nao iniciado (%s); inferencia local continua.\n", esp_err_to_name(mqtt_err));
    }

    const esp_err_t rpm_err = configure_e18_rpm();
    if (rpm_err != ESP_OK) {
        ei_printf("Falha ao iniciar E18/RPM: %s\n", esp_err_to_name(rpm_err));
        return;
    }

    const esp_err_t ntc_err = configure_ntc();
    if (ntc_err != ESP_OK) {
        ei_printf("Falha ao iniciar NTC: %s\n", esp_err_to_name(ntc_err));
        return;
    }

    const uint32_t sample_interval_us =
        static_cast<uint32_t>(EI_CLASSIFIER_INTERVAL_MS) * 1000U;

    const esp_err_t imu_err = imu_config_init(sample_interval_us);
    if (imu_err != ESP_OK) {
        ei_printf("Falha ao iniciar IMU: %s\n", esp_err_to_name(imu_err));
        return;
    }

    serial_protocol_metadata();

    size_t feature_ix = 0;

    while (true) {
        imu_sample_t sample;

        if (xQueueReceive(imu_queue, &sample, portMAX_DELAY) != pdPASS) {
            continue;
        }

        /* RPM e independente da IA: pulsos sao contados pela ISR. */
        update_rpm_if_due();

        /* Uma linha @S por amostra; o backend usa accel XYZ para sinal/RMS. */
        serial_protocol_sample(sample);

        if (feature_ix + EI_CLASSIFIER_RAW_SAMPLES_PER_FRAME >
            EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
            feature_ix = 0;
        }

        features[feature_ix++] = sample.accel_x;
        features[feature_ix++] = sample.accel_y;
        features[feature_ix++] = sample.accel_z;
        features[feature_ix++] = sample.gyro_x;
        features[feature_ix++] = sample.gyro_y;
        features[feature_ix++] = sample.gyro_z;

        if (feature_ix != EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
            continue;
        }

        signal_t signal;
        signal.total_length = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE;
        signal.get_data = raw_feature_get_data;

        ei_impulse_result_t result = {0};
        const EI_IMPULSE_ERROR res = run_classifier(&signal, &result, false);

        if (res != EI_IMPULSE_OK) {
            ei_printf("run_classifier falhou: %d\n", res);
        }
        else {
            /*
             * Temperatura e lida uma vez por janela de inferencia.
             * Isso evita inserir leituras ADC no caminho de aquisicao a 100 Hz.
             */
            const esp_err_t temp_err = read_temperature();
            if (temp_err != ESP_OK) {
                ei_printf("Falha ao ler NTC: %s\n", esp_err_to_name(temp_err));
            }

            update_rpm_if_due();
            print_classifier_result(result);
        }

        /* Janela nao sobreposta: proximo frame comeca na proxima amostra. */
        feature_ix = 0;
    }
}
