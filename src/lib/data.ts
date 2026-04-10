import type { Conference, OutletStats, ReporterStats } from "./types";

const conferenceFiles = import.meta.glob("../data/conferences/*.json", {
  eager: true,
});

export function getAllConferences(): Conference[] {
  return Object.values(conferenceFiles)
    .map((mod: any) => mod.default)
    .sort((a, b) => b.meta.date.localeCompare(a.meta.date));
}

export function getConference(date: string): Conference | undefined {
  return getAllConferences().find((c) => c.meta.date === date);
}

import outletsData from "../data/generated/outlets_stats.json";
import reportersData from "../data/generated/reporters.json";

export const outlets: OutletStats[] = outletsData;
export const reporters: ReporterStats[] = reportersData;
