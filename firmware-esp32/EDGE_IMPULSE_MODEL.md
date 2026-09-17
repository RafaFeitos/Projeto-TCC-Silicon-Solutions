# Atualizacao do modelo Edge Impulse

Este firmware foi preparado para modelos de vibracao com exatamente tres eixos:
`accel_x + accel_y + accel_z`.

O modelo atualmente embarcado foi exportado do projeto Edge Impulse
"Projeto PNAAT Vibração Máquina BNO085" e possui:

- 100 Hz;
- intervalo de 10 ms;
- 100 amostras por janela;
- 3 eixos por amostra;
- 300 floats por frame.

## Trocar por uma nova versao do mesmo tipo de modelo

Exporte o novo impulse no Edge Impulse como **C++ Library** e substitua, em conjunto:

- `components/edge-impulse-sdk/`
- `components/model-parameters/`
- `components/tflite-model/`

Nao substitua apenas o arquivo `.tflite`: `model-parameters` contem metadados,
classes, configuracao DSP, frequencia e dimensoes que precisam corresponder ao modelo.

O `main.cpp` le automaticamente do modelo:

- `EI_CLASSIFIER_INTERVAL_MS`;
- `EI_CLASSIFIER_RAW_SAMPLE_COUNT`;
- `EI_CLASSIFIER_RAW_SAMPLES_PER_FRAME`;
- `EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE`;
- `EI_CLASSIFIER_LABEL_COUNT`.

Se o novo modelo deixar de usar tres eixos de aceleracao, a compilacao falhara de
proposito no `static_assert`, pois o firmware precisara ser adaptado ao novo contrato
de entrada.

## Build e gravacao

Com ESP-IDF 5.x configurado:

```bash
idf.py set-target esp32s3
idf.py fullclean
idf.py build
idf.py -p PORT flash monitor
```

O BNO085 e configurado usando o mesmo intervalo de amostragem declarado pelo
modelo Edge Impulse e envia aceleracao calibrada (m/s^2) nos eixos X/Y/Z.
