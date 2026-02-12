export default async function Home() {
  let api: any = null;
  try {
    const res = await fetch("http://127.0.0.1:8000/health", { cache: "no-store" });
    api = await res.json();
  } catch (e) {
    api = { ok: false, error: "API not reachable" };
  }

  return (
    <main style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700 }}>NextLayer Admin Dashboard</h1>
      <pre style={{ marginTop: 16, background: "#111", color: "#0f0", padding: 16, borderRadius: 12 }}>
        {JSON.stringify(api, null, 2)}
      </pre>
    </main>
  );
}
