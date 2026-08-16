import { Feather } from "@expo/vector-icons";
import React from "react";
import { Linking, Platform, Pressable, StyleSheet, Text, View } from "react-native";

export type Hotspot = { label: string; count: number; latitude: number; longitude: number; severity?: number };

const GREEN = "#15803d";

export function openDirections(lat: number, lng: number, label: string) {
  const q = encodeURIComponent(label || "Hotspot");
  const url = Platform.select({
    ios: `http://maps.apple.com/?daddr=${lat},${lng}&q=${q}`,
    android: `geo:${lat},${lng}?q=${lat},${lng}(${q})`,
    default: `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`,
  }) as string;
  Linking.openURL(url).catch(() => Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`));
}

export function severityColor(sev?: number) {
  if ((sev ?? 0) >= 8) return "#dc2626";
  if ((sev ?? 0) >= 6) return "#f59e0b";
  return "#0284c7";
}

// Rendered on web and inside Expo Go where native maps do not load.
export function HotspotFallback({ hotspots, note }: { hotspots: Hotspot[]; note?: string }) {
  return (
    <View testID="hotspot-map" style={styles.card}>
      <View style={styles.mapGrid}>
        <View style={styles.roadA} />
        <View style={styles.roadB} />
        {hotspots.map((h, i) => (
          <View key={`${h.label}-${i}`} style={[styles.pin, { left: `${18 + (i * 19) % 67}%`, top: `${22 + (i * 23) % 52}%` }]}>
            <View style={[styles.pinBubble, { backgroundColor: severityColor(h.severity) }]}><Feather name="map-pin" size={15} color="#fff" /></View>
            <Text style={styles.pinCount}>{h.count}</Text>
          </View>
        ))}
        {note ? <View style={styles.noteChip}><Feather name="smartphone" size={12} color="#475569" /><Text style={styles.noteText}>{note}</Text></View> : null}
      </View>
      <View style={styles.list}>
        {hotspots.length === 0 ? (
          <Text style={styles.emptyText}>No active hotspots right now.</Text>
        ) : hotspots.map((h, i) => (
          <View key={`row-${h.label}-${i}`} style={styles.row}>
            <View style={[styles.dot, { backgroundColor: severityColor(h.severity) }]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel} numberOfLines={1}>{h.label}</Text>
              <Text style={styles.rowMeta}>{h.count} open · max severity {h.severity ?? "-"}</Text>
            </View>
            <Pressable testID={`directions-${i}`} onPress={() => openDirections(h.latitude, h.longitude, h.label)} style={({ pressed }) => [styles.dirButton, pressed && { opacity: 0.7 }]}>
              <Feather name="navigation" size={14} color={GREEN} />
              <Text style={styles.dirText}>Directions</Text>
            </Pressable>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: "#dbeafe", borderRadius: 19, overflow: "hidden", borderWidth: 1, borderColor: "#bfdbfe" },
  mapGrid: { height: 176, backgroundColor: "#e0f2fe", position: "relative", overflow: "hidden" },
  roadA: { position: "absolute", width: "150%", height: 24, backgroundColor: "#fff", top: 70, left: -40, transform: [{ rotate: "-12deg" }] },
  roadB: { position: "absolute", width: "125%", height: 18, backgroundColor: "#fff", top: 105, left: -30, transform: [{ rotate: "32deg" }] },
  pin: { position: "absolute", alignItems: "center" },
  pinBubble: { width: 31, height: 31, borderRadius: 16, borderWidth: 3, borderColor: "#fff", alignItems: "center", justifyContent: "center" },
  pinCount: { color: "#0f172a", fontSize: 10, fontWeight: "900", marginTop: 2, backgroundColor: "rgba(255,255,255,.85)", paddingHorizontal: 4, borderRadius: 5 },
  noteChip: { position: "absolute", bottom: 10, left: 10, right: 10, backgroundColor: "rgba(255,255,255,.92)", borderRadius: 9, paddingVertical: 6, paddingHorizontal: 9, flexDirection: "row", alignItems: "center", gap: 6 },
  noteText: { color: "#475569", fontSize: 11, fontWeight: "700", flex: 1 },
  list: { backgroundColor: "#fff", padding: 8 },
  emptyText: { color: "#94a3b8", fontSize: 13, padding: 12, textAlign: "center" },
  row: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, paddingHorizontal: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: "#f1f5f9" },
  dot: { width: 10, height: 10, borderRadius: 5 },
  rowLabel: { color: "#0f172a", fontWeight: "800", fontSize: 13 },
  rowMeta: { color: "#64748b", fontSize: 11, marginTop: 2 },
  dirButton: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderColor: "#bbf7d0", borderRadius: 10, paddingHorizontal: 11, minHeight: 38, backgroundColor: "#f0fdf4" },
  dirText: { color: GREEN, fontWeight: "800", fontSize: 12 },
});
