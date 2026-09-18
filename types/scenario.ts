// Global Policy Radar — scenario engine contracts.
// Additive schema: existing dashboard/scenario_state fields remain valid.

export type CountryCode = "CN" | "US" | "EU" | "JP" | "KR" | "IN" | "RU" | "GB" | "AU" | "ME" | "OTHER";
export type EventCategory = "POLITICS" | "ECONOMY" | "FINANCE" | "TRADE" | "TARIFF" | "PORT" | "LOGISTICS" | "GEOPOLITICS" | "ENERGY" | "CRITICAL_MINERALS" | "TECHNOLOGY" | "SANCTIONS" | "PAYMENT" | "CURRENCY";
export type Horizon = "T1D" | "T7D" | "T15D" | "T30D" | "T180D" | "T365D";
export type ScenarioType = "HARD_DECOUPLING" | "STRUCTURAL_NEGOTIATION" | "THIRD_PARTY_DIVERSION";
export type ActionDomain = "INVESTMENT" | "TRADE" | "LIFE";
export type ActionPolarity = "DO" | "DONT" | "WATCH";
export type ConfidenceLevel = "LOW" | "MEDIUM" | "HIGH";

export interface GlobalEvent {
  id: string;
  title: string;
  summary: string;
  category: EventCategory | string;
  importance: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  actor: { type: "COUNTRY" | "REGION" | "INTERNATIONAL_ORG" | "COMPANY" | "CENTRAL_BANK" | "MARKET" | "NON_STATE_ACTOR"; country?: CountryCode; name: string };
  affectedCountries: CountryCode[];
  source: { provider: string; url?: string; publishedAt: string; fetchedAt: string; credibility: number };
  status: "RUMOR" | "DEVELOPING" | "CONFIRMED" | "RESOLVED";
  triggerRole: "PRIMARY_TRIGGER" | "CATALYST" | "BACKGROUND" | "NO_DIRECT_LINK";
  impact: { china: number; us: number; globalTrade: number; logistics: number; finance: number; energy: number; technology: number };
  channels: ImpactChannel[];
  tags: string[];
}

export interface ImpactChannel {
  id: string;
  name: "TRADE" | "SUPPLY_CHAIN" | "SHIPPING" | "ENERGY" | "MINERALS" | "TECH" | "CAPITAL" | "PAYMENT" | "FX" | "SANCTIONS";
  intensity: number;
  description: string;
}

export interface ActorResponse {
  id: string;
  round: 1 | 2 | 3;
  actor: CountryCode | string;
  responseType: string;
  title: string;
  description: string;
  triggerEventIds: string[];
  expectedTargets: string[];
  intensity: number;
  expectedTiming: Horizon;
  impacts: { trade: number; currency: number; equities: number; bonds: number; commodities: number; crypto: number; logistics: number };
  confidence: ConfidenceLevel;
}

export type EvidenceLevel = "FACT" | "SIGNAL" | "INFERENCE" | "ASSUMPTION" | "UNKNOWN";

export interface ScenarioChainNode {
  id: string;
  order: number;
  actor: string;
  action: string;
  mechanism: string;
  consequence: string;
  nextNodeIds: string[];
  affectedDomains: ActionDomain[];
  evidenceLevel?: EvidenceLevel;
  evidenceEventIds?: string[];
  caveat?: string;
}

export interface ActionItem {
  id: string;
  polarity: ActionPolarity;
  title: string;
  action: string;
  rationale: string;
  urgency: "LOW" | "MEDIUM" | "HIGH" | "IMMEDIATE";
  conditions?: string[];
  risks?: string[];
  relatedSignals?: string[];
  tags?: string[];
}

export interface ActionSection {
  domain: ActionDomain;
  do: ActionItem[];
  dont: ActionItem[];
  watch: ActionItem[];
}

export interface ActionMatrix {
  investment: ActionSection;
  trade: ActionSection;
  life: ActionSection;
}

export interface Signal {
  id: string;
  name: string;
  metric: string;
  currentValue?: number;
  threshold?: number;
  unit?: string;
  direction: "UP" | "DOWN" | "VOLATILE" | "BREAKOUT" | "STABLE";
  importance: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface ScenarioHorizon {
  horizon: Horizon;
  label: string;
  startOffsetDays: number;
  endOffsetDays: number;
  keySignals: Signal[];
  impacts: { domain: ActionDomain; direction: "POSITIVE" | "NEGATIVE" | "MIXED" | "UNCERTAIN"; intensity: number; explanation: string }[];
  actions: ActionMatrix;
}

export interface Scenario {
  id: string;
  type: ScenarioType;
  code: "A" | "B" | "C";
  title: string;
  description: string;
  prerequisites: string[];
  triggers: { eventId?: string; condition: string; threshold?: number; direction: "ABOVE" | "BELOW" | "INCREASE" | "DECREASE" | "OCCUR" | "FAIL" }[];
  chain: ScenarioChainNode[];
  confidence: ConfidenceLevel;
  sensitivity: number;
  activationState: "WATCH" | "ACTIVE" | "ELEVATED";
  triggerScore: number;
  triggerEvidence: string[];
  counterSignals: string[];
  recomputeIf: string[];
  horizons: ScenarioHorizon[];
}

export interface ScenarioSnapshotItem {
  id: string;
  code: "A" | "B" | "C";
  activationState: "WATCH" | "ACTIVE" | "ELEVATED";
  triggerScore: number;
  triggerEvidence: string[];
  counterSignals: string[];
  evidenceDrivers?: EvidenceDriver[];
}

export interface ScenarioSnapshot {
  generatedAt: string;
  scenarios: ScenarioSnapshotItem[];
  eventEvidence?: { id: string; title: string; publishedAt?: string; fetchedAt?: string; tier?: "PRIMARY" | "KNOWN_MEDIA" | "UNKNOWN"; freshness?: "NEW" | "RECENT" | "STALE" | "UNKNOWN"; dedupeKey?: string }[];
}

export interface EvidenceDriver {
  kind: "EVENT" | "MARKET";
  id?: string;
  title?: string;
  source?: string;
  url?: string;
  role?: string;
  category?: string;
  name?: string;
  value?: unknown;
  change_pct?: number;
  publishedAt?: string;
  fetchedAt?: string;
  tier?: "PRIMARY" | "KNOWN_MEDIA" | "UNKNOWN";
  freshness?: "NEW" | "RECENT" | "STALE" | "UNKNOWN";
  credibility?: number;
}

export interface ScenarioHistoryChange {
  id: string;
  code: "A" | "B" | "C";
  previousState: "WATCH" | "ACTIVE" | "ELEVATED";
  currentState: "WATCH" | "ACTIVE" | "ELEVATED";
  previousScore: number;
  currentScore: number;
  delta: number;
  reasons: string[];
  evidenceDrivers?: EvidenceDriver[];
  counterSignals: string[];
}

export interface ScenarioHistory {
  baseline: "FIRST_RUN" | "COMPARISON";
  previousGeneratedAt: string | null;
  changes: ScenarioHistoryChange[];
  newEvidence?: { id: string; title: string; publishedAt?: string; fetchedAt?: string; tier?: "PRIMARY" | "KNOWN_MEDIA" | "UNKNOWN"; freshness?: "NEW" | "RECENT" | "STALE" | "UNKNOWN"; dedupeKey?: string }[];
  staleOrRemovedEvidence?: { id: string; title: string; publishedAt?: string; fetchedAt?: string; tier?: "PRIMARY" | "KNOWN_MEDIA" | "UNKNOWN"; freshness?: "NEW" | "RECENT" | "STALE" | "UNKNOWN"; dedupeKey?: string }[];
}

export interface ScenarioTree {
  id: string;
  rootEventId: string;
  title: string;
  rounds: { round: 1 | 2 | 3; actor: string; title: string; responseIds: string[] }[];
  scenarios: Scenario[];
  generatedAt: string;
  modelVersion: string;
}

export interface IntelligenceScenarioV2 {
  schema_version: "2.0";
  generatedAt: string;
  version: string;
  globalEvents: GlobalEvent[];
  responses: ActorResponse[];
  scenarioTree: ScenarioTree;
  state: Record<string, unknown>;
  scenarioSnapshot: ScenarioSnapshot;
  scenarioHistory: ScenarioHistory;
  dashboard: {
    headline: string;
    triggerEvents: string[];
    activeScenarios: string[];
    immediateActions: string[];
    warnings: string[];
  };
  legacy: {
    events: unknown[];
    scenarios: unknown[];
    signals: unknown[];
    action_framework: unknown;
  };
}
