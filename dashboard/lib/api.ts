import type {
  CurrentState,
  DatasetInfo,
  Inference,
  MachineCreate,
  MachineInfo,
  MachineMetrics,
  OverviewResponse,
  ProductionUpdate,
  StreamStatus,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getDataset(): Promise<DatasetInfo> {
  const res = await fetch(`${API_URL}/api/dataset`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

export async function getState(): Promise<CurrentState | null> {
  const res = await fetch(`${API_URL}/api/state`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

export async function getHistory(): Promise<Inference[]> {
  const res = await fetch(`${API_URL}/api/history?limit=120`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

async function post(path: string): Promise<void> {
  let res: Response;

  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
    });
  } catch {
    throw new Error(
      `Não foi possível conectar à API em ${API_URL}. Inicie o backend antes de usar o replay.`,
    );
  }

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    
    throw new Error(
      `API retornou ${res.status}${detail ? `: ${detail}` : ""}`,
    );
  }
}

export async function startReplay() {
  await post("/api/replay/start");
}

export async function stopReplay() {
  await post("/api/replay/stop");
}

export async function resetReplay() {
  await post("/api/replay/reset");
}
export async function getMachines(): Promise<MachineInfo[]> {
  const res = await fetch(`${API_URL}/api/machines`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function registerMachine(
  machine: MachineCreate,
): Promise<MachineInfo> {
  const res = await fetch(`${API_URL}/api/machines`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(machine),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function getOverview(): Promise<OverviewResponse> {
  const res = await fetch(`${API_URL}/api/overview`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function getMachineState(
  machineId: number,
): Promise<CurrentState | null> {
  const res = await fetch(
    `${API_URL}/api/machines/${machineId}/state`,
    {
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function getMachineHistory(
  machineId: number,
): Promise<Inference[]> {
  const res = await fetch(
    `${API_URL}/api/machines/${machineId}/history?limit=120`,
    {
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function getMachineMetrics(
  machineId: number,
): Promise<MachineMetrics> {
  const res = await fetch(
    `${API_URL}/api/machines/${machineId}/metrics`,
    {
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function getMachineStatus(
  machineId: number,
): Promise<StreamStatus> {
  const res = await fetch(
    `${API_URL}/api/machines/${machineId}/status`,
    {
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function updateProduction(
  machineId: number,
  production: ProductionUpdate,
): Promise<MachineMetrics> {
  const res = await fetch(
    `${API_URL}/api/machines/${machineId}/production`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(production),
    },
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function startMachineReplay(machineId: number) {
  await post(`/api/machines/${machineId}/replay/start`);
}

export async function stopMachineReplay(machineId: number) {
  await post(`/api/machines/${machineId}/replay/stop`);
}

export async function resetMachineReplay(machineId: number) {
  await post(`/api/machines/${machineId}/replay/reset`);
}