export const PRESET_KEYS = [
  "birth_date",
  "region",
  "card_issue_date",
  "join_date",
  "chairman",
] as const;

export type PresetKey = (typeof PRESET_KEYS)[number];

export function defaultFieldOrder(): PresetKey[] {
  return [...PRESET_KEYS];
}

export function normaliseFieldOrder(input: string[] | null | undefined): PresetKey[] {
  const known = new Set<string>(PRESET_KEYS);
  const seen = new Set<string>();
  const out: PresetKey[] = [];
  for (const k of input ?? []) {
    if (known.has(k) && !seen.has(k)) {
      out.push(k as PresetKey);
      seen.add(k);
    }
  }
  for (const k of PRESET_KEYS) {
    if (!seen.has(k)) out.push(k);
  }
  return out;
}

export type OrderedField<T extends { key: string }> =
  | { kind: "preset"; key: PresetKey }
  | { kind: "custom"; field: T };

export function buildFieldRenderOrder<T extends { key: string }>(
  fieldOrder: string[] | null | undefined,
  labelSet: T[],
): OrderedField<T>[] {
  const presetSet = new Set<string>(PRESET_KEYS);
  const customByKey = new Map(labelSet.map((f) => [f.key, f]));
  const seen = new Set<string>();
  const out: OrderedField<T>[] = [];
  for (const k of fieldOrder ?? []) {
    if (seen.has(k)) continue;
    if (presetSet.has(k)) {
      out.push({ kind: "preset", key: k as PresetKey });
      seen.add(k);
    } else if (customByKey.has(k)) {
      out.push({ kind: "custom", field: customByKey.get(k)! });
      seen.add(k);
    }
  }
  for (const k of PRESET_KEYS) {
    if (!seen.has(k)) {
      out.push({ kind: "preset", key: k });
      seen.add(k);
    }
  }
  for (const f of labelSet) {
    if (!seen.has(f.key)) {
      out.push({ kind: "custom", field: f });
      seen.add(f.key);
    }
  }
  return out;
}
