const cache = new Map<string, string>();

export async function deriveAddress(walletId: string): Promise<string> {
  const cached = cache.get(walletId);
  if (cached) return cached;
  const bytes = new TextEncoder().encode(walletId);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  const addr = "0x" + hex.slice(0, 40);
  cache.set(walletId, addr);
  return addr;
}

export function truncateAddress(addr: string, head = 6, tail = 4): string {
  if (addr.length <= head + tail + 1) return addr;
  return `${addr.slice(0, head)}…${addr.slice(-tail)}`;
}
