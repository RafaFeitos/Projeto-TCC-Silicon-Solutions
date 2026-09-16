"use client";

import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import InferenceList from "../components/InferenceList";
import SignalChart from "../components/SignalChart";
import StatusBadge from "../components/StatusBadge";

import {
  API_URL,
  getMachineHistory,
  getMachineMetrics,
  getMachineState,
  getMachineStatus,
  getMachines,
  getOverview,
  registerMachine,
  resetMachineReplay,
  startMachineReplay,
  stopMachineReplay,
} from "../lib/api";

import type {
  CurrentState,
  Inference,
  MachineCreate,
  MachineInfo,
  MachineMetrics,
  OverviewResponse,
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
  rpm_raw: null,
  rpm_filtered: null,
  rpm_pulses: null,
  rpm_pulse_hz: null,
  temperature_c: null,
  ntc_raw: null,
  ntc_voltage: null,
  ntc_resistance: null,
};

function emptyStateFor(
  machine?: MachineInfo | null,
): CurrentState {
  return {
    ...emptyState,
    machine_id: machine?.id ?? 1,
    machine_name:
      machine?.name ?? "Máquina 01",
  };
}

type Tab =
  | "machine"
  | "overview";

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

function formatPercent(
  value: number | null | undefined,
) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${value.toFixed(1)}%`;
}


function formatHours(
  value: number | null | undefined,
) {
  if (value === null || value === undefined) {
    return "Sem falhas";
  }

  return `${value.toFixed(1)} h`;
}

function formatRpm(
  value?: number | null,
) {
  return value == null
    ? "—"
    : `${value.toFixed(0)} rpm`;
}


function formatTemperature(
  value?: number | null,
) {
  return value == null
    ? "—"
    : `${value.toFixed(1)} °C`;
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
    rpm_raw: value.rpm_raw ?? null,
    rpm_filtered: value.rpm_filtered ?? null,
    rpm_pulses: value.rpm_pulses ?? null,
    rpm_pulse_hz: value.rpm_pulse_hz ?? null,
    temperature_c: value.temperature_c ?? null,
    ntc_raw: value.ntc_raw ?? null,
    ntc_voltage: value.ntc_voltage ?? null,
    ntc_resistance: value.ntc_resistance ?? null,
  };
}


export default function Home() {
const [tab, setTab] =
  useState<Tab>("overview");

const [machines, setMachines] =
  useState<MachineInfo[]>([]);

const [selectedMachineId, setSelectedMachineId] =
  useState(1);

const [overview, setOverview] =
  useState<OverviewResponse | null>(null);

const [metrics, setMetrics] =
  useState<MachineMetrics | null>(null);

const [state, setState] =
  useState<CurrentState>(emptyState);

const [history, setHistory] =
  useState<Inference[]>([]);

const [running, setRunning] =
  useState(false);

const [error, setError] =
  useState("");

const [hydrated, setHydrated] =
  useState(false);

const [showMachineForm, setShowMachineForm] =
  useState(false);

const [newMachine, setNewMachine] =
  useState<MachineCreate>({
    name: "",
    ideal_cycle_time_seconds: null,
    total_count: 0,
    good_count: 0,
  });

const selectedMachine = useMemo(
  () =>
    machines.find(
      (machine) =>
        machine.id === selectedMachineId,
    ) ??
    machines[0] ??
    null,
  [machines, selectedMachineId],
);

useEffect(() => {
  setHydrated(true);

  Promise.all([
    getMachines(),
    getOverview(),
  ])
    .then(([machineList, overviewData]) => {
      setMachines(machineList);
      setOverview(overviewData);

      if (machineList.length > 0) {
        setSelectedMachineId(
          machineList[0].id,
        );
      }
    })
    .catch((err) =>
      setError(
        err instanceof Error
          ? err.message
          : "Erro ao conectar à API",
      ),
    );
}, []);


useEffect(() => {
  if (!selectedMachine) {
    return;
  }

  const machineId =
    selectedMachine.id;

  Promise.all([
    getMachineHistory(machineId),
    getMachineState(machineId),
    getMachineMetrics(machineId),
    getMachineStatus(machineId),
  ])
    .then(
      ([
        machineHistory,
        current,
        machineMetrics,
        machineStatus,
      ]) => {
        setHistory(machineHistory);
        setMetrics(machineMetrics);
        setRunning(machineStatus.running);

        if (current) {
          setState(
            normalizeState(current),
          );
        } else {
          setState(
            emptyStateFor(
              selectedMachine,
            ),
          );
        }
      },
    )
    .catch((err) =>
      setError(
        err instanceof Error
          ? err.message
          : "Erro ao carregar máquina",
      ),
    );


  const source = new EventSource(
    `${API_URL}/api/machines/${machineId}/stream`,
  );

  source.onmessage = (event) => {
    const item =
      JSON.parse(event.data) as Inference;

    setState(
      normalizeState({
        ...item,
        machine_name:
          selectedMachine.name,
      }),
    );

    setHistory((previous) =>
      [...previous, item].slice(-120),
    );

    getMachineMetrics(machineId)
      .then(setMetrics)
      .catch(() => {});

    getOverview()
      .then(setOverview)
      .catch(() => {});
  };

  source.onerror = () =>
    setError(
      "API desconectada — confira se o backend está rodando na porta 8000.",
    );

  return () => {
    source.close();
  };
}, [
  selectedMachineId,
  selectedMachine?.name,
]);

const alertCount =
  overview?.metrics.alert_count ?? 0;


const runningCount =
  overview?.metrics.operating_count ?? 0;


  const confidence = Math.max(
    0,
    Math.min(1, state.confidence),
  );


  async function handleStart() {
    setError("");

    try {
      await startMachineReplay(
        selectedMachineId,
      );
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
      await stopMachineReplay(
        selectedMachineId,
      );
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
      await resetMachineReplay(
        selectedMachineId,
      );

      setHistory([]);
      setState(
        emptyStateFor(selectedMachine),
      );
      setMetrics(
        selectedMachine
          ? await getMachineMetrics(
            selectedMachine.id,
          )
          : null,
      );

      setOverview(await getOverview());
      
      setRunning(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não foi possível reiniciar o replay.",
      );
    }
  }
async function handleRegisterMachine(
  event: FormEvent<HTMLFormElement>,
) {
  event.preventDefault();

  setError("");

  if (
    newMachine.good_count >
    newMachine.total_count
  ) {
    setError(
      "A produção boa não pode ser maior que a produção total.",
    );

    return;
  }

  try {
    const created =
      await registerMachine(
        newMachine,
      );

    const [
      machineList,
      overviewData,
    ] = await Promise.all([
      getMachines(),
      getOverview(),
    ]);

    setMachines(machineList);
    setOverview(overviewData);

    setSelectedMachineId(
      created.id,
    );

    setState(
      emptyStateFor(created),
    );

    setHistory([]);
    setMetrics(null);

    setNewMachine({
      name: "",
      ideal_cycle_time_seconds:
        null,
      total_count: 0,
      good_count: 0,
    });

    setShowMachineForm(false);
    setTab("machine");
  } catch (err) {
    setError(
      err instanceof Error
        ? err.message
        : "Não foi possível cadastrar a máquina.",
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

            {machines.map((machine) => (
              <button
                key={machine.id}
                className={
                  tab === "machine" &&
                  selectedMachineId ===
                    machine.id
                    ? "tab active"
                    : "tab"
                }
                onClick={() => {
                  setSelectedMachineId(
                    machine.id,
                  );

                  setTab("machine");
                }}
              >
                {machine.name}
              </button>
            ))}

            <button
              className="tab tab-add"
              title="Adicionar máquina"
              onClick={() =>
                setShowMachineForm(
                  (value) => !value,
                )
              }
            >
              +
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


      {showMachineForm ? (
        <form
          className="machine-form panel"
          onSubmit={handleRegisterMachine}
        >
          <div className="panel-head">
            <div>
              <span className="eyebrow">
                NOVO EQUIPAMENTO
              </span>

              <h2>Registrar máquina</h2>
            </div>
          </div>


          <div className="machine-form-grid">
            <label className="machine-field">
              <span>Nome</span>

              <input
                value={newMachine.name ?? ""}
                placeholder="Máquina 02"
                onChange={(event) =>
                  setNewMachine({
                    ...newMachine,
                    name: event.target.value,
                  })
                }
              />
            </label>


            <label className="machine-field">
              <span>Ciclo ideal (s)</span>

              <input
                type="number"
                min="0.001"
                step="0.001"
                value={
                  newMachine.ideal_cycle_time_seconds ??
                  ""
                }
                onChange={(event) =>
                  setNewMachine({
                    ...newMachine,
                    ideal_cycle_time_seconds:
                      event.target.value
                        ? Number(event.target.value)
                        : null,
                  })
                }
              />
            </label>


            <label className="machine-field">
              <span>Produção total</span>

              <input
                type="number"
                min="0"
                value={newMachine.total_count}
                onChange={(event) =>
                  setNewMachine({
                    ...newMachine,
                    total_count: Number(
                      event.target.value,
                    ),
                  })
                }
              />
            </label>


            <label className="machine-field">
              <span>Produção boa</span>

              <input
                type="number"
                min="0"
                value={newMachine.good_count}
                onChange={(event) =>
                  setNewMachine({
                    ...newMachine,
                    good_count: Number(
                      event.target.value,
                    ),
                  })
                }
              />
            </label>
          </div>


          <div className="machine-form-actions">
            <button
              type="button"
              className="ghost"
              onClick={() =>
                setShowMachineForm(false)
              }
            >
              Cancelar
            </button>

            <button
              type="submit"
              className="control"
            >
              Registrar máquina
            </button>
          </div>
        </form>
      ) : null}


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
              {overview?.metrics.machine_count ?? 0}{" "}
              máquinas registradas
            </span>
          </div>


          <section className="kpis">
            <div className="kpi">
              <span>OEE</span>

              <strong>
                {formatPercent(
                  overview?.metrics.oee,
                )}
              </strong>

              <small>
                eficiência geral das máquinas
              </small>
            </div>


            <div className="kpi">
              <span>MTBF</span>

              <strong>
                {formatHours(
                  overview?.metrics.mtbf_hours,
                )}
              </strong>

              <small>
                tempo médio entre falhas
              </small>
            </div>


            <div className="kpi">
              <span>MÁQUINAS</span>

              <strong>
                {runningCount}/
                {overview?.metrics.machine_count ?? 0}
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
                alertas ativos
              </small>
            </div>
          </section>


          <section className="overview-machines">
            {(overview?.machines ?? []).map(
              (summary) => (
                <div
                  className="panel machine-summary"
                  key={summary.machine.id}
                >
                  <div className="panel-head">
                    <div>
                      <span className="eyebrow">
                        MÁQUINA
                      </span>

                      <h2>
                        {summary.machine.name}
                      </h2>
                    </div>

                    <StatusBadge
                      state={
                        summary.state?.state ??
                        "AGUARDANDO"
                      }
                      severity={
                        summary.state?.severity ??
                        null
                      }
                    />
                  </div>


                  <div className="machine-summary-body">
                    <div>
                      <span className="metric-label">
                        OEE
                      </span>

                      <strong>
                        {formatPercent(
                          summary.metrics.oee,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span className="metric-label">
                        MTBF
                      </span>

                      <strong>
                        {formatHours(
                          summary.metrics.mtbf_hours,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span className="metric-label">
                        RPM
                      </span>
                    <strong>
                      {formatRpm(
                        summary.state?.rpm_filtered,
                      )}
                    </strong>
                    </div>
                    <div>
                      <span className="metric-label">
                        Temperatura
                      </span>
                    <strong>
                      {formatTemperature(
                        summary.state?.temperature_c,
                      )}
                    </strong>
                    </div>
                    <div>
                      <span className="metric-label">
                        Disponibilidade
                      </span>

                      <strong>
                        {formatPercent(
                          summary.metrics.availability,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span className="metric-label">
                        Falhas
                      </span>

                      <strong>
                        {summary.metrics.failure_count}
                      </strong>
                    </div>
                  </div>


                  <button
                    className="inline-action"
                    onClick={() => {
                      setSelectedMachineId(
                        summary.machine.id,
                      );

                      setTab("machine");
                    }}
                  >
                    Abrir {summary.machine.name}
                    <span>→</span>
                  </button>
                </div>
              ),
            )}

            {!overview?.machines.length ? (
              <div className="panel empty">
                Nenhuma máquina registrada.
              </div>
            ) : null}
          </section>
        </section>
      )}


      {tab === "machine" && (
        <section className="page-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                MÁQUINA
              </span>

              <h2>
                {selectedMachine?.name ??
                  "Máquina"}
              </h2>
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
            <div className="kpi">
              <span>RPM</span>
              <strong className="value-mono">
                {formatRpm(state.rpm_filtered)}
              </strong>

              <small>
                E18-D80NK · valor filtrado
              </small>
            </div>
            <div className="kpi">
              <span>TEMPERATURA</span>

              <strong className="value-mono">
                {formatTemperature(state.temperature_c)}
              </strong>

              <small>
                NTC 10K MF52
              </small>
            </div>
          </section>


          <section className="kpis metrics-kpis">
            <div className="kpi">
              <span>OEE</span>

              <strong>
                {formatPercent(metrics?.oee)}
              </strong>

              <small>
                eficiência geral
              </small>
            </div>


            <div className="kpi">
              <span>MTBF</span>

              <strong>
                {formatHours(metrics?.mtbf_hours)}
              </strong>

              <small>
                tempo médio entre falhas
              </small>
            </div>


            <div className="kpi">
              <span>DISPONIBILIDADE</span>

              <strong>
                {formatPercent(
                  metrics?.availability,
                )}
              </strong>
            </div>


            <div className="kpi">
              <span>PERFORMANCE</span>

              <strong>
                {formatPercent(
                  metrics?.performance,
                )}
              </strong>
            </div>


            <div className="kpi">
              <span>QUALIDADE</span>

              <strong>
                {formatPercent(
                  metrics?.quality,
                )}
              </strong>
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


              <div className="metric-strip telemetry-strip">
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
                    RPM filtrado
                  </span>

                  <strong>
                    {formatRpm(state.rpm_filtered)}
                  </strong>
                </div>

                <div>
                  <span>
                    Temperatura
                  </span>

                  <strong>
                    {formatTemperature(state.temperature_c)}
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
                <span>RPM bruto</span>
                  <strong>
                    {formatRpm(state.rpm_raw)}
                  </strong>
                </div>
                <div>
                  <span>Frequência E18</span>

                  <strong>
                    {state.rpm_pulse_hz == null
                      ? "—"
                      : `${state.rpm_pulse_hz.toFixed(2)} Hz`}
                  </strong>
                </div>
                <div>
                  <span>Temperatura</span>

                  <strong>
                    {formatTemperature(state.temperature_c)}
                  </strong>
                </div>

                <div>
                  <span>Dataset</span>

                  <strong>
                    {selectedMachine
                      ?.dataset_file ??
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
                    {selectedMachine
                      ?.dataset_file ?? "—"}
                  </strong>
                </div>

                <div>
                  <span>Produção total</span>

                  <strong>
                    {metrics?.total_count ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Produção boa</span>

                  <strong>
                    {metrics?.good_count ?? 0}
                  </strong>
                </div>

                <div>
                  <span>Ciclo ideal</span>

                  <strong>
                    {metrics
                      ?.ideal_cycle_time_seconds
                      ? `${metrics.ideal_cycle_time_seconds} s`
                      : "—"}
                  </strong>
                </div>
              </div>
            </div>
          </section>
        </section>
      )}


      <footer>
        Industrial Monitor ·{" "}
        {machines.length}{" "}
        {machines.length === 1
          ? "máquina"
          : "máquinas"}{" "}
        · FastAPI · Next.js
      </footer>
    </main>
  );
}