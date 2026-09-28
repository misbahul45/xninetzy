import type { AssetData } from "./types";

export type AssetIndex = Map<string, AssetData>;

export function buildAssetIndex(assets: AssetData[]): AssetIndex {
  const idx = new Map<string, AssetData>();
  for (const a of assets) {
    idx.set(a.asset_id, a);
  }
  return idx;
}
