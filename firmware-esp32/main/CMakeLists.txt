set(MODEL_FOLDER ../components)
set(EI_SDK_FOLDER ../components/edge-impulse-sdk)

set(include_dirs
    ${MODEL_FOLDER}
    ${MODEL_FOLDER}/tflite-model
    ${MODEL_FOLDER}/model-parameters
    ${EI_SDK_FOLDER}
    ${EI_SDK_FOLDER}/porting/espressif/esp-dsp/modules/fft/include
    ${EI_SDK_FOLDER}/porting/espressif/esp-dsp/modules/common/include
)

include(${EI_SDK_FOLDER}/cmake/utils.cmake)

# Edge Impulse SDK / TFLite sources. CMSIS is not used on ESP32-S3.
RECURSIVE_FIND_FILE_EXCLUDE_DIR(EI_CPP_FILES "../components/edge-impulse-sdk" "CMSIS" "*.cpp")
RECURSIVE_FIND_FILE_EXCLUDE_DIR(EI_CC_FILES  "../components/edge-impulse-sdk" "CMSIS" "*.cc")
RECURSIVE_FIND_FILE_EXCLUDE_DIR(EI_C_FILES   "../components/edge-impulse-sdk" "CMSIS" "*.c")
RECURSIVE_FIND_FILE_EXCLUDE_DIR(MODEL_FILES  "../components/tflite-model" "CMSIS" "*.cpp")

# Optimized Espressif kernels contain both .s and .S files.
RECURSIVE_FIND_FILE_EXCLUDE_DIR(ESP_NN_S_FILES
    "${EI_SDK_FOLDER}/porting/espressif/ESP-NN" "CMSIS" "*.s")
RECURSIVE_FIND_FILE_EXCLUDE_DIR(ESP_NN_S_UPPER_FILES
    "${EI_SDK_FOLDER}/porting/espressif/ESP-NN" "CMSIS" "*.S")
RECURSIVE_FIND_FILE_EXCLUDE_DIR(ESP_DSP_S_FILES
    "${EI_SDK_FOLDER}/porting/espressif/esp-dsp/modules/fft" "CMSIS" "*.s")
RECURSIVE_FIND_FILE_EXCLUDE_DIR(ESP_DSP_S_UPPER_FILES
    "${EI_SDK_FOLDER}/porting/espressif/esp-dsp/modules/fft" "CMSIS" "*.S")

set(EI_SOURCE_FILES
    ${EI_CPP_FILES}
    ${EI_CC_FILES}
    ${EI_C_FILES}
    ${MODEL_FILES}
    ${ESP_NN_S_FILES}
    ${ESP_NN_S_UPPER_FILES}
    ${ESP_DSP_S_FILES}
    ${ESP_DSP_S_UPPER_FILES}
)

idf_component_register(
    SRCS
        "main.cpp"
        "imu_config.c"
        "mqtt_manager.c"
        ${EI_SOURCE_FILES}
    INCLUDE_DIRS
        "."
        ${include_dirs}
    PRIV_REQUIRES
        bno085
        freertos
        esp_timer
        esp_adc
        driver
        log
        esp_wifi
        esp_event
        esp_netif
        nvs_flash
        mqtt
)

target_compile_definitions(${COMPONENT_LIB} PRIVATE
    EI_CLASSIFIER_TFLITE_ENABLE_ESP_NN=1
    EIDSP_USE_ESP_DSP=1
)

if(${IDF_TARGET} STREQUAL "esp32s3")
    target_compile_definitions(${COMPONENT_LIB} PRIVATE
        EI_CLASSIFIER_TFLITE_ENABLE_ESP_NN_S3=1
    )
endif()

target_compile_options(${COMPONENT_LIB} PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:-std=gnu++17>
    -Wno-maybe-uninitialized
    -Wno-missing-field-initializers
)
