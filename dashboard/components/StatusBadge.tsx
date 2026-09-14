export default function StatusBadge({
  state,
  severity,
}: {
  state: string;
  severity?: string | null;
}) {
  const critical =
    severity === "CRITICAL" || state === "FALHA";

  const warning =
    !critical &&
    (severity === "WARNING" || state === "ANOMALIA");

  const cls = critical
    ? "critical"
    : warning
      ? "warning"
      : "ok";

  const label =
    state === "AGUARDANDO"
      ? "AGUARDANDO"
      : state;

  return (
    <span className={`status-badge ${cls}`}>
      <i />
      {label}
    </span>
  );
}