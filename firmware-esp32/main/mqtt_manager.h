#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H
#include <stdbool.h>
#include "esp_err.h"
#ifdef __cplusplus
extern "C" {
#endif
esp_err_t mqtt_manager_start(void);
bool mqtt_manager_is_connected(void);
esp_err_t mqtt_manager_publish(const char *payload);
#ifdef __cplusplus
}
#endif
#endif
