export type AgentId =
  | "ProjectManager_001"
  | "MarketResearcher_001"
  | "ContentWriter_001"
  | "WebDeveloper_001"
  | "Designer_001"
  | "QAJudge_001"
  | "ContentWriter_002"
  | "WebDeveloper_002"
  | "Designer_002";

interface Persona {
  short: string;        // 8–12 words · tooltip / inline
  full: string;         // 2–4 sentence dossier blurb
  style: string;        // Bidding-style chip text
  voice: string;        // Short voice tag
  archetype: string;    // 1–2 word category label
  walletId: string;
}

export const PERSONAS: Record<string, Persona> = {
  ProjectManager_001: {
    short: "Aggressive project manager · 15–22% margin · ruthless on scope.",
    full:
      "Hard-nosed project manager who runs the marketplace. Decomposes jobs into DAGs, hires sub-agents, takes a 15–22% margin. Ruthless on scope creep, generous on reputation for premium delivery.",
    style: "AGGRESSIVE BIDDER",
    voice: "direct, numbers-first",
    archetype: "PM",
    walletId: "wallet_projectmanager_001",
  },
  MarketResearcher_001: {
    short: "McKinsey-grade analyst · precise · honest about uncertainty.",
    full:
      "Disciplined market researcher. Cites sources, quantifies uncertainty, declines tasks outside scope. Base price $20 per task, predictable bidder with mid-tier reputation (0.76).",
    style: "ANALYTICAL",
    voice: "calm, evidence-first",
    archetype: "Researcher",
    walletId: "wallet_marketresearcher_001",
  },
  ContentWriter_001: {
    short: "David Ogilvy meets a modern conversion strategist.",
    full:
      "Premium copywriter with 62 completed jobs and a 0.88 reputation. Charges 15–20% above market rate — reputation outweighs price in the rerank. Specializes in landing-page copy and persuasive narrative.",
    style: "PREMIUM",
    voice: "punchy, conversion-focused",
    archetype: "Premium writer",
    walletId: "wallet_contentwriter_001",
  },
  WebDeveloper_001: {
    short: "Pragmatic senior frontend dev · ships running HTML.",
    full:
      "Critical-path skill — every STANDARD job depends on the webdev to ship the final artifact. Volume bidder, base price $45, mid-tier reputation (0.79), 85% success.",
    style: "VOLUME",
    voice: "pragmatic, terse, code-first",
    archetype: "Developer",
    walletId: "wallet_webdeveloper_001",
  },
  Designer_001: {
    short: "Hungry junior designer · underdog discount · hex-fluent.",
    full:
      "Underdog designer with 0.71 reputation. Auto-discounts 10% when reputation < 0.80 to win bids. Hungry, improving, sometimes plays it safe with generic palettes and gets revision-requested.",
    style: "UNDERDOG",
    voice: "earnest, design-system literate",
    archetype: "Underdog designer",
    walletId: "wallet_designer_001",
  },
  QAJudge_001: {
    short: "Senior reviewer · evidence-based · $2 flat per verdict.",
    full:
      "The marketplace's only judge. Applies a 4-criterion rubric (scope 0.25 · structure 0.20 · content 0.35 · brief fidelity 0.20). Charges $2 flat regardless of verdict — no incentive to approve or reject. Cites exact evidence in reasoning.",
    style: "AUTO-INVOKED",
    voice: "judicial, evidence-cites",
    archetype: "Judge",
    walletId: "wallet_qajudge_001",
  },
  ContentWriter_002: {
    short: "Ghost copywriter · rule-based bid at 65% of budget.",
    full:
      "Marketplace-depth bidder. Bids exactly 65% of task budget on every copy task to keep the marketplace feeling competitive. Filtered before reranking per spec §16-A5 — cannot win execution.",
    style: "GHOST · RULE-BASED",
    voice: "deterministic, no-op",
    archetype: "Ghost writer",
    walletId: "wallet_contentwriter_002",
  },
  WebDeveloper_002: {
    short: "Ghost developer · rule-based bid at 95% of budget.",
    full:
      "Marketplace-depth bidder. Bids exactly 95% of task budget on every webdev task. Filtered before reranking per spec §16-A5 — cannot win execution.",
    style: "GHOST · RULE-BASED",
    voice: "deterministic, no-op",
    archetype: "Ghost developer",
    walletId: "wallet_webdeveloper_002",
  },
  Designer_002: {
    short: "Ghost designer · rule-based bid at 90% of budget.",
    full:
      "Marketplace-depth bidder. Bids exactly 90% of task budget on every design task. Filtered before reranking per spec §16-A5 — cannot win execution.",
    style: "GHOST · RULE-BASED",
    voice: "deterministic, no-op",
    archetype: "Ghost designer",
    walletId: "wallet_designer_002",
  },
};

export const ROSTER_ORDER: string[] = [
  "ProjectManager_001",
  "MarketResearcher_001",
  "ContentWriter_001",
  "WebDeveloper_001",
  "Designer_001",
  "QAJudge_001",
  "ContentWriter_002",
  "WebDeveloper_002",
  "Designer_002",
];
