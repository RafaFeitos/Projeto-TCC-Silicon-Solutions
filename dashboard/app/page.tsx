"use client";

import { useEffect, useMemo, useState } from "react";

import InferenceList from "../components/InferenceList";
import SignalChart from "../components/SignalChart";
import StatusBadge from "../components/StatusBadge";

import {
  API_URL,
  getDataset,
  getHistory,
  getState,
  resetReplay,
  startReplay,
  stopReplay,
} from "../lib/api";

import type {
  CurrentState,
  DatasetInfo,
  Inference,
} from "../lib/types";


const emptyState: CurrentState = {
  machine_id: 1,
  machine_name: "Máquina 01",
  state: "AGUARDANDO",
  confidence: 0,
  predicted_class: "AGUARDANDO",
  model_version: "—",
  source: "—",
  signal_value: 0,
  rms: 0,
  timestamp: "",
  alert: null,
  severity: null,
};


type Tab =
  | "machine"
  | "overview"
  | "dataset"
  | "inferences";


function formatTime(value: string) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleTimeString("pt-BR");
}


function classLabel(value: string) {
  return value.replaceAll("_", " ");
}


function normalizeState(
  value: Partial<CurrentState>,
): CurrentState {
  return {
    machine_id: Number(value.machine_id ?? 1),
    machine_name: value.machine_name ?? "Máquina 01",
    state: value.state ?? "AGUARDANDO",
    confidence: Number(value.confidence ?? 0),
    predicted_class:
      value.predicted_class ?? "AGUARDANDO",
    model_version: value.model_version ?? "—",
    source: value.source ?? "—",
    signal_value: Number(value.signal_value ?? 0),
    rms: Number(value.rms ?? 0),
    timestamp: value.timestamp ?? "",
    alert: value.alert ?? null,
    severity: value.severity ?? null,
  };
}


export default function Home() {
  const [tab, setTab] = useState<Tab>("machine");

  const [state, setState] =
    useState<CurrentState>(emptyState);

  const [history, setHistory] =
    useState<Inference[]>([]);

  const [dataset, setDataset] =
    useState<DatasetInfo | null>(null);

  const [running, setRunning] =
    useState(false);

  const [error, setError] =
    useState("");

  const [hydrated, setHydrated] =
    useState(false);


  useEffect(() => {
    setHydrated(true);

    Promise.all([
      getDataset(),
      getHistory(),
      getState(),
    ])
      .then(([ds, hist, current]) => {
        setDataset(ds);
        setHistory(hist);

        if (current) {
          setState(normalizeState(current));
        }
      })
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "Erro ao conectar à API",
        ),
      );


    const source =
      new EventSource(`${API_URL}/api/stream`);


    source.onmessage = (event) => {
      const item =
        JSON.parse(event.data) as Inference;

      const normalized = normalizeState({
        ...item,
        machine_name: "Máquina 01",
      });

      setState(normalized);

      setHistory((previous) =>
        [...previous, item].slice(-120),
      );
    };


    source.onerror = () =>
      setError(
        "API desconectada — confira se o backend está rodando na porta 8000.",
      );


    return () => {
      source.close();
    };
  }, []);


  const alertCount = useMemo(
    () =>
      history.filter(
        (item) => item.alert,
      ).length,
    [history],
  );


  const runningCount =
    state.state === "OPERANDO" ? 1 : 0;


  const confidence = Math.max(
    0,
    Math.min(1, state.confidence),
  );


  async function handleStart() {
    setError("");

    try {
      await startReplay();
      setRunning(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não foi possível iniciar o replay.",
      );
    }
  }


  async function handleStop() {
    try {
      await stopReplay();
      setRunning(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não foi possível parar o replay.",
      );
    }
  }


  async function handleReset() {
    setError("");

    try {
      await resetReplay();

      setHistory([]);
      setState(emptyState);
      setRunning(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não foi possível reiniciar o replay.",
      );
    }
  }


  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-line">
            <span
              className="brand-mark"
              aria-hidden="true"
            >
              ▦
            </span>

            <span className="eyebrow">
              INDUSTRIAL MONITOR
            </span>
          </div>

          <h1>Monitoramento de Máquinas</h1>

          <p>
            Monitoramento operacional de
            equipamentos legados por inferência
            de vibração.
          </p>

          <nav
            className="tabs"
            aria-label="Navegação principal"
          >
            <button
              className={
                tab === "overview"
                  ? "tab active"
                  : "tab"
              }
              onClick={() =>
                setTab("overview")
              }
            >
              Visão geral
            </button>

            <button
              className={
                tab === "machine"
                  ? "tab active"
                  : "tab"
              }
              onClick={() =>
                setTab("machine")
              }
            >
              Máquina 01
            </button>

            <button
              className={
                tab === "dataset"
                  ? "tab active"
                  : "tab"
              }
              onClick={() =>
                setTab("dataset")
              }
            >
              Dataset
            </button>

            <button
              className={
                tab === "inferences"
                  ? "tab active"
                  : "tab"
              }
              onClick={() =>
                setTab("inferences")
              }
            >
              Inferências
            </button>
          </nav>
        </div>


        <div className="controls">
          <span
            className={
              running
                ? "connection live"
                : "connection"
            }
          >
            <i />

            {running
              ? "REPLAY ATIVO"
              : "PARADO"}
          </span>

          <button
            className="ghost"
            onClick={handleReset}
          >
            Reiniciar
          </button>

          {running ? (
            <button
              className="control"
              onClick={handleStop}
            >
              Parar
            </button>
          ) : (
            <button
              className="control"
              onClick={handleStart}
            >
              Iniciar replay
            </button>
          )}
        </div>
      </header>


      {error ? (
        <div className="error-banner">
          {error}
        </div>
      ) : null}


      {tab === "overview" && (
        <section className="page-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                PAINEL
              </span>

              <h2>Visão geral</h2>
            </div>

            <span className="section-note">
              1 máquina monitorada
            </span>
          </div>


          <section className="kpis">
            <div className="kpi">
              <span>ESTADO ATUAL</span>

              <StatusBadge
                state={state.state}
                severity={state.severity}
              />

              <small>
                {classLabel(
                  state.predicted_class,
                )}
              </small>
            </div>


            <div className="kpi">
              <span>CONFIANÇA</span>

              <strong>
                {Math.round(
                  confidence * 100,
                )}
                %
              </strong>

              <div className="progress">
                <i
                  style={{
                    width: `${
                      confidence * 100
                    }%`,
                  }}
                />
              </div>
            </div>


            <div className="kpi">
              <span>MÁQUINAS</span>

              <strong>
                {runningCount}/1
              </strong>

              <small>
                operando neste instante
              </small>
            </div>


            <div className="kpi">
              <span>ALERTAS</span>

              <strong>
                {alertCount}
              </strong>

              <small>
                detectados no replay
              </small>
            </div>
          </section>


          <section className="overview-grid">
            <div className="panel machine-summary">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">
                    ATIVO
                  </span>

                  <h2>Máquina 01</h2>
                </div>

                <StatusBadge
                  state={state.state}
                  severity={
                    state.severity
                  }
                />
              </div>


              <div className="machine-summary-body">
                <div>
                  <span className="metric-label">
                    Equipamento
                  </span>

                  <strong>
                    Máquina 01
                  </strong>
                </div>

                <div>
                  <span className="metric-label">
                    Leitura atual
                  </span>

                  <strong>
                    {state.signal_value.toFixed(
                      4,
                    )}
                  </strong>
                </div>

                <div>
                  <span className="metric-label">
                    RMS móvel
                  </span>

                  <strong>
                    {state.rms.toFixed(4)}
                  </strong>
                </div>

                <div>
                  <span className="metric-label">
                    Última inferência
                  </span>

                  <strong>
                    {hydrated
                      ? formatTime(
                          state.timestamp,
                        )
                      : "—"}
                  </strong>
                </div>
              </div>


              <button
                className="inline-action"
                onClick={() =>
                  setTab("machine")
                }
              >
                Abrir máquina 01
                <span>→</span>
              </button>
            </div>


            <div className="panel">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">
                    EVENTOS
                  </span>

                  <h2>
                    Alertas recentes
                  </h2>
                </div>

                <button
                  className="text-button"
                  onClick={() =>
                    setTab("inferences")
                  }
                >
                  Ver tudo
                </button>
              </div>


              <div className="compact-list">
                {history
                  .filter(
                    (item) => item.alert,
                  )
                  .slice(-5)
                  .reverse()
                  .map(
                    (item, index) => (
                      <div
                        className="compact-row"
                        key={`${item.timestamp}-${index}`}
                      >
                        <div>
                          <strong>
                            {item.alert}
                          </strong>

                          <span>
                            {hydrated
                              ? formatTime(
                                  item.timestamp,
                                )
                              : "—"}
                          </span>
                        </div>

                        <span className="severity-text">
                          {item.severity ??
                            "—"}
                        </span>
                      </div>
                    ),
                  )}

                {!history.some(
                  (item) => item.alert,
                ) ? (
                  <div className="empty">
                    Nenhum alerta
                    registrado.
                  </div>
                ) : null}
              </div>
            </div>
          </section>
        </section>
      )}


      {tab === "machine" && (
        <section className="page-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                MÁQUINA 01
              </span>

              <h2>Máquina 01</h2>
            </div>

            <span className="section-note">
              Fonte:{" "}
              {state.source || "—"}
            </span>
          </div>


          <section className="kpis machine-kpis">
            <div className="kpi">
              <span>ESTADO ATUAL</span>

              <StatusBadge
                state={state.state}
                severity={state.severity}
              />

              <small>
                {classLabel(
                  state.predicted_class,
                )}
              </small>
            </div>


            <div className="kpi">
              <span>CONFIANÇA</span>

              <strong>
                {Math.round(
                  confidence * 100,
                )}
                %
              </strong>

              <div className="progress">
                <i
                  style={{
                    width: `${
                      confidence * 100
                    }%`,
                  }}
                />
              </div>
            </div>


            <div className="kpi">
              <span>
                LEITURA ATUAL
              </span>

              <strong className="value-mono">
                {state.signal_value.toFixed(
                  4,
                )}
              </strong>

              <small>
                amplitude do sinal
              </small>
            </div>


            <div className="kpi">
              <span>RMS MÓVEL</span>

              <strong className="value-mono">
                {state.rms.toFixed(4)}
              </strong>

              <small>
                janela recente
              </small>
            </div>
          </section>


          <section className="grid-main">
            <div className="panel large">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">
                    SINAL DO SENSOR
                  </span>

                  <h2>Vibração</h2>
                </div>

                <span className="live-indicator">
                  <i />

                  {running
                    ? "REPLAY"
                    : "PAUSADO"}
                </span>
              </div>


              <SignalChart
                data={history}
              />


              <div className="metric-strip">
                <div>
                  <span>
                    Leitura atual
                  </span>

                  <strong>
                    {state.signal_value.toFixed(
                      4,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    RMS móvel
                  </span>

                  <strong>
                    {state.rms.toFixed(
                      4,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Última inferência
                  </span>

                  <strong>
                    {hydrated
                      ? formatTime(
                          state.timestamp,
                        )
                      : "—"}
                  </strong>
                </div>
              </div>
            </div>


            <div className="panel">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">
                    ESTADO
                  </span>

                  <h2>
                    Interpretação
                  </h2>
                </div>
              </div>


              {state.alert ? (
                <div
                  className={`alert-card ${
                    state.severity ===
                    "CRITICAL"
                      ? "alert-critical"
                      : "alert-warning"
                  }`}
                >
                  <span className="alert-symbol">
                    !
                  </span>

                  <div>
                    <strong>
                      {state.alert}
                    </strong>

                    <p>
                      Alerta derivado da
                      inferência atual.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="safe-card">
                  <span>✓</span>

                  <div>
                    <strong>
                      Nenhum alerta ativo
                    </strong>

                    <p>
                      A última janela não
                      apresentou anomalia
                      operacional.
                    </p>
                  </div>
                </div>
              )}


              <div className="info-list">
                <div>
                  <span>
                    Classe atual
                  </span>

                  <strong>
                    {classLabel(
                      state.predicted_class,
                    )}
                  </strong>
                </div>

                <div>
                  <span>Modelo</span>

                  <strong>
                    {state.model_version}
                  </strong>
                </div>

                <div>
                  <span>Fonte</span>

                  <strong>
                    {state.source}
                  </strong>
                </div>

                <div>
                  <span>Dataset</span>

                  <strong>
                    {dataset?.file_name ??
                      "aguardando CSV"}
                  </strong>
                </div>
              </div>
            </div>
          </section>


          <section className="lower-grid">
            <div className="panel">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">
                    HISTÓRICO
                  </span>

                  <h2>
                    Últimas inferências
                  </h2>
                </div>

                <button
                  className="text-button"
                  onClick={() =>
                    setTab("inferences")
                  }
                >
                  Abrir histórico
                </button>
              </div>

              <InferenceList
                data={history.slice(-6)}
              />
            </div>


            <div className="panel mini-panel">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">
                    ORIGEM
                  </span>

                  <h2>Dataset</h2>
                </div>
              </div>

              <div className="dataset-quick">
                <div>
                  <span>Arquivo</span>

                  <strong>
                    {dataset?.file_name ??
                      "Nenhum CSV detectado"}
                  </strong>
                </div>

                <div>
                  <span>Sinal</span>

                  <strong>
                    {dataset?.signal_column ??
                      "—"}
                  </strong>
                </div>

                <div>
                  <span>Amostras</span>

                  <strong>
                    {dataset?.rows ??
                      "—"}
                  </strong>
                </div>
              </div>
            </div>
          </section>
        </section>
      )}


      {tab === "dataset" && (
        <section className="page-section narrow-page">
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                DADOS
              </span>

              <h2>Dataset</h2>
            </div>

            <span className="section-note">
              Origem da leitura utilizada
            </span>
          </div>


          <div className="panel dataset-panel">
            <div className="dataset-header">
              <div>
                <span className="eyebrow">
                  ARQUIVO ATIVO
                </span>

                <h3>
                  {dataset?.file_name ??
                    "Nenhum CSV detectado"}
                </h3>
              </div>

              <span className="file-state">
                <i />
                detectado
              </span>
            </div>


            <div className="dataset-grid">
              <div>
                <span>
                  Linhas válidas
                </span>

                <strong>
                  {dataset?.rows ?? "—"}
                </strong>
              </div>

              <div>
                <span>
                  Coluna do sinal
                </span>

                <strong>
                  {dataset?.signal_column ??
                    "—"}
                </strong>
              </div>

              <div>
                <span>
                  Coluna de rótulo
                </span>

                <strong>
                  {dataset?.label_column ??
                    "não informado"}
                </strong>
              </div>

              <div>
                <span>
                  Coluna temporal
                </span>

                <strong>
                  {dataset?.timestamp_column ??
                    "não informado"}
                </strong>
              </div>
            </div>


            <div className="column-list">
              <span className="eyebrow">
                COLUNAS ENCONTRADAS
              </span>

              <div className="tags">
                {(dataset?.columns ?? []).map(
                  (column) => (
                    <span key={column}>
                      {column}
                    </span>
                  ),
                )}
              </div>
            </div>


            <div className="pipeline">
              <span>CSV</span>
              <b>→</b>
              <span>Replay</span>
              <b>→</b>
              <span>Inferência</span>
              <b>→</b>
              <span>Estado</span>
              <b>→</b>
              <span>Dashboard</span>
            </div>
          </div>
        </section>
      )}


      {tab === "inferences" && (
        <section className="page-section narrow-page">
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                MODELO
              </span>

              <h2>
                Inferências recentes
              </h2>
            </div>

            <span className="section-note">
              Últimas {history.length} leituras
              recebidas
            </span>
          </div>

          <div className="panel">
            <InferenceList
              data={[...history]
                .reverse()
                .slice(0, 40)}
            />
          </div>
        </section>
      )}


      <footer>
        Máquina 01 · FastAPI · Next.js
      </footer>
    </main>
  );
}