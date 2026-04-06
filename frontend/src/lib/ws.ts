export function buildWebSocketUrl(path: string) {
  const baseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
  return `${baseUrl}${path}`;
}
