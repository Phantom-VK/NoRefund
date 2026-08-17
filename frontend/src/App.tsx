export default function App() {
  const bridged =
    typeof window !== "undefined" && "pywebview" in window ? "yes" : "no";
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2">
      <h1 className="text-2xl font-bold">NoRefund</h1>
      <p className="text-sm opacity-60">Phase 01 — foundation</p>
      <p className="text-xs opacity-40">bridge present: {bridged}</p>
    </div>
  );
}
