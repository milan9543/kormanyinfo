import type { Conference, OutletStats, ReporterStats, MinisterInterview } from "./types";

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

const ministerFiles = import.meta.glob("../data/minister_interviews/*.json", {
  eager: true,
});

function slugifyCandidate(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9\-]/g, "");
}

export function getAllMinisterInterviews(): MinisterInterview[] {
  return Object.values(ministerFiles)
    .map((mod: any) => mod.default)
    .sort((a, b) => b.meta.date.localeCompare(a.meta.date));
}

export function getMinisterInterview(slug: string): MinisterInterview | undefined {
  return getAllMinisterInterviews().find(
    (m) => `${m.meta.date}_${slugifyCandidate(m.meta.candidate)}` === slug,
  );
}

export function ministerInterviewSlug(interview: MinisterInterview): string {
  return `${interview.meta.date}_${slugifyCandidate(interview.meta.candidate)}`;
}
