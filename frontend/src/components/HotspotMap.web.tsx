import React from "react";

import { Hotspot, HotspotFallback } from "./HotspotShared";

// Web has no native map; render the hotspot list + directions fallback.
export default function HotspotMap({ hotspots }: { hotspots: Hotspot[] }) {
  return <HotspotFallback hotspots={hotspots} />;
}
