export type Tier = "REJECTED" | "MINIMAL" | "STANDARD" | "PREMIUM";

export interface TierMath {
  tier: Tier;
  margin: number;       // 0 for REJECTED
  numTasks: number;     // 0 for REJECTED
  pmBid: number;        // budget × (1 − margin × 0.5)
  subAgentPool: number; // pmBid × (1 − margin)
  judgeReserve: number; // numTasks × $2
  expectedRefund: number; // budget − pmBid (for REJECTED: full budget)
}

const TASKS_BY_TIER: Record<Tier, number> = {
  REJECTED: 0,
  MINIMAL: 2,
  STANDARD: 4,
  PREMIUM: 5, // midpoint of 4–6
};

const MARGIN_BY_TIER: Record<Tier, number> = {
  REJECTED: 0,
  MINIMAL: 0.15,
  STANDARD: 0.18,
  PREMIUM: 0.22,
};

export function tierFor(budget: number): Tier {
  if (budget < 50) return "REJECTED";
  if (budget < 150) return "MINIMAL";
  if (budget < 500) return "STANDARD";
  return "PREMIUM";
}

export function computeTier(budget: number): TierMath {
  const tier = tierFor(budget);
  const margin = MARGIN_BY_TIER[tier];
  const numTasks = TASKS_BY_TIER[tier];

  if (tier === "REJECTED") {
    return {
      tier,
      margin: 0,
      numTasks: 0,
      pmBid: 0,
      subAgentPool: 0,
      judgeReserve: 0,
      expectedRefund: budget,
    };
  }

  const pmBid = round2(budget * (1 - margin * 0.5));
  const subAgentPool = round2(pmBid * (1 - margin));
  const judgeReserve = round2(numTasks * 2);
  const expectedRefund = round2(budget - pmBid);

  return { tier, margin, numTasks, pmBid, subAgentPool, judgeReserve, expectedRefund };
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export function formatMoney(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
