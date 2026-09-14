import type { CurrentState, DatasetInfo, Inference } from "./types";

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