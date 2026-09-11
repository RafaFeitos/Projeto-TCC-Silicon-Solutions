from datetime import datetime, timezone

from app.inference.dataset_adapter import Sample, infer_window


def test_demo_normal():
    samples = [
        Sample(datetime.now(timezone.utc), 0.05),
        Sample(datetime.now(timezone.utc), 0.07),
    ]
    result = infer_window(samples)
    assert result["predicted_class"] == "NORMAL"
    assert result["state"] == "OPERANDO"


def test_demo_anomaly():
    samples = [
        Sample(datetime.now(timezone.utc), 1.0),
        Sample(datetime.now(timezone.utc), 1.2),
    ]
    result = infer_window(samples)
    assert result["predicted_class"] == "VIBRACAO_ANORMAL"
    assert result["state"] == "ANOMALIA"
    assert result["alert"]
