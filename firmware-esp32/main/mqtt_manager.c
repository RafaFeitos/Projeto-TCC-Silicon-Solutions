#include "mqtt_manager.h"
#include <string.h>
#include "sdkconfig.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "mqtt_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

static const char *TAG = "mqtt";
static EventGroupHandle_t s_wifi_events;
static esp_mqtt_client_handle_t s_mqtt;
static volatile bool s_connected;
#define WIFI_OK BIT0

static void wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data) {
    (void)arg; (void)data;
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) esp_wifi_connect();
    else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        s_connected = false;
        esp_wifi_connect();
    }
    else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) xEventGroupSetBits(s_wifi_events, WIFI_OK);
}

static void mqtt_event(void *args, esp_event_base_t base, int32_t event_id, void *event_data) {
    (void)args; (void)base; (void)event_data;
    if (event_id == MQTT_EVENT_CONNECTED) { s_connected = true; ESP_LOGI(TAG, "MQTT conectado"); }
    else if (event_id == MQTT_EVENT_DISCONNECTED) { s_connected = false; ESP_LOGW(TAG, "MQTT desconectado"); }
}

esp_err_t mqtt_manager_start(void) {
#if !CONFIG_PNAAT_MQTT_ENABLE
    ESP_LOGI(TAG, "MQTT desabilitado no menuconfig");
    return ESP_OK;
#else
    if (strlen(CONFIG_PNAAT_WIFI_SSID) == 0 || strlen(CONFIG_PNAAT_MQTT_BROKER_URI) == 0) {
        ESP_LOGW(TAG, "Configure Wi-Fi e broker em Component config > PNAAT connectivity");
        return ESP_ERR_INVALID_STATE;
    }
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) { ESP_ERROR_CHECK(nvs_flash_erase()); err = nvs_flash_init(); }
    ESP_ERROR_CHECK(err);
    ESP_ERROR_CHECK(esp_netif_init());
    esp_err_t loop_err = esp_event_loop_create_default();
    if (loop_err != ESP_OK && loop_err != ESP_ERR_INVALID_STATE) ESP_ERROR_CHECK(loop_err);
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    s_wifi_events = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event, NULL));
    wifi_config_t wc = {0};
    strlcpy((char *)wc.sta.ssid, CONFIG_PNAAT_WIFI_SSID, sizeof(wc.sta.ssid));
    strlcpy((char *)wc.sta.password, CONFIG_PNAAT_WIFI_PASSWORD, sizeof(wc.sta.password));
    wc.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wc));
    ESP_ERROR_CHECK(esp_wifi_start());
    EventBits_t bits = xEventGroupWaitBits(s_wifi_events, WIFI_OK, pdFALSE, pdFALSE, pdMS_TO_TICKS(15000));
    if (!(bits & WIFI_OK)) { ESP_LOGW(TAG, "Wi-Fi ainda nao conectado; MQTT nao iniciado"); return ESP_ERR_TIMEOUT; }

    esp_mqtt_client_config_t mc = {0};
    mc.broker.address.uri = CONFIG_PNAAT_MQTT_BROKER_URI;
#if CONFIG_PNAAT_MQTT_AUTH
    mc.credentials.username = CONFIG_PNAAT_MQTT_USERNAME;
    mc.credentials.authentication.password = CONFIG_PNAAT_MQTT_PASSWORD;
#endif
    s_mqtt = esp_mqtt_client_init(&mc);
    if (!s_mqtt) return ESP_ERR_NO_MEM;
    ESP_ERROR_CHECK(esp_mqtt_client_register_event(s_mqtt, MQTT_EVENT_ANY, mqtt_event, NULL));
    return esp_mqtt_client_start(s_mqtt);
#endif
}

bool mqtt_manager_is_connected(void) { return s_connected; }

esp_err_t mqtt_manager_publish(const char *payload) {
#if !CONFIG_PNAAT_MQTT_ENABLE
    (void)payload; return ESP_ERR_NOT_SUPPORTED;
#else
    if (!s_mqtt || !s_connected || !payload) return ESP_ERR_INVALID_STATE;
    int id = esp_mqtt_client_publish(s_mqtt, CONFIG_PNAAT_MQTT_TOPIC, payload, 0, 1, 0);
    return id >= 0 ? ESP_OK : ESP_FAIL;
#endif
}
