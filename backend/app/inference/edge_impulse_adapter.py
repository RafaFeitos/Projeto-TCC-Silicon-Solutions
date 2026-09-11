"""
Substituir apenas o corpo de `predict` quando o pacote/exportação real do modelo
estiver disponível.
"""

class EdgeImpulseAdapter:
    model_version = "edge_impulse_pending"

    def predict(self, signal_window: list[float]) -> dict:
        raise NotImplementedError(
            "Conecte aqui o modelo/exportação real do Edge Impulse. "
            "Enquanto isso, use o modo DEMO do Dataset Adapter."
        )