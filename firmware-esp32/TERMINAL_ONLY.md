# Firmware ESP32-S3 — BNO085 + Edge Impulse + Serial

Esta versao nao usa OLED ou LVGL.

```text
BNO085 (I2C) -> accel_x/y/z -> Edge Impulse -> terminal/USB Serial
```

## Pinagem

- VCC -> 3V3
- GND -> GND
- SDA -> GPIO6
- SCL -> GPIO7
- INT -> GPIO5
- RST -> GPIO4
- ADR -> GND (`0x4A`)

## Protocolo serial

O firmware mantem logs legiveis para humanos e tambem emite linhas reservadas para o backend:

```text
@M,<projeto>,<deploy_version>,<samples>,<eixos>,<interval_ms>
@S,<timestamp_us>,<accel_x>,<accel_y>,<accel_z>
@I,<timestamp_us>,<classe>,<confianca>,<deploy_version>
```

O backend ignora as demais linhas de log.

## Build

```powershell
idf.py fullclean
idf.py set-target esp32s3
idf.py build
idf.py -p COM5 flash
```

Depois do flash, feche o monitor serial antes de iniciar o backend do dashboard.
