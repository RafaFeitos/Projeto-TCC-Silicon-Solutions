# Integração BNO085 + Edge Impulse + RPM + Temperatura

## Hardware mantido dos testes validados

- BNO085: aquisição usada pelo modelo Edge Impulse, no intervalo definido pelo próprio modelo (100 Hz na versão atual).
- E18-D80NK: GPIO3, interrupção por borda de descida.
- Disco de RPM: 4 furos simétricos = 4 pulsos por volta.
- NTC 10K MF52: GPIO2 / ADC1_CHANNEL_1.
- Divisor NTC: resistor fixo de 5,1 kOhm para 3V3.
- Beta usado no teste: 3950.

## Cálculo de RPM

RPM = frequência_de_pulsos * 60 / 4

A janela é de aproximadamente 1 segundo e o cálculo usa o tempo real em microssegundos.
Foi preservado o filtro:
RPM_filtrado = 0,70 * anterior + 0,30 * atual

## Organização

O BNO085 continua sendo adquirido pela task FreeRTOS existente.
O E18 conta pulsos por interrupção, sem bloquear a aquisição da IMU.
O NTC é lido uma vez por janela de inferência.

A saída do terminal agora apresenta, para cada inferência:
- probabilidades das classes;
- classe vencedora e confiança;
- RPM bruto e filtrado;
- pulsos e frequência do E18;
- temperatura do NTC;
- timing do Edge Impulse.

## Build

idf.py set-target esp32s3
idf.py build
idf.py flash monitor
