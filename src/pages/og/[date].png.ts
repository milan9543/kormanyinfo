import type { APIRoute } from "astro";
import satori from "satori";
import { Resvg } from "@resvg/resvg-js";
import { getAllConferences, getConference } from "../../lib/data";

export function getStaticPaths() {
  return getAllConferences().map((c) => ({ params: { date: c.meta.date } }));
}

async function loadGoogleFont(family: string, weight: number): Promise<ArrayBuffer> {
  const css = await fetch(
    `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:wght@${weight}`,
    { headers: { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" } }
  ).then((r) => r.text());
  const url = css.match(/src: url\((.+?)\) format/)?.[1];
  if (!url) throw new Error(`Font URL not found for ${family} ${weight}`);
  return fetch(url).then((r) => r.arrayBuffer());
}

export const GET: APIRoute = async ({ params }) => {
  const conf = getConference(params.date!);
  if (!conf) return new Response("Not found", { status: 404 });

  const qCount = conf.questions.length;
  const reporterCount = new Set(conf.questions.map((q) => q.reporter)).size;
  const outletCount = new Set(conf.questions.map((q) => q.outlet)).size;
  const avgCrit = Math.round(
    conf.questions.reduce((s, q) => s + q.criticism_percent, 0) / qCount
  );
  const avgHost = Math.round(
    conf.questions.reduce((s, q) => s + q.hostility_percent, 0) / qCount
  );
  const maxCrit = Math.max(...conf.questions.map((q) => q.criticism_percent));

  const [playfair, sourceSans] = await Promise.all([
    loadGoogleFont("Playfair Display", 700),
    loadGoogleFont("Source Sans 3", 400),
  ]);

  const stats = [
    { value: String(qCount), label: "Kérdés" },
    { value: String(reporterCount), label: "Újságíró" },
    { value: String(outletCount), label: "Médium" },
    { value: `${avgCrit}%`, label: "Átl. kritikusság" },
    { value: `${avgHost}%`, label: "Átl. ellenségesség" },
    { value: `${maxCrit}%`, label: "Max kritikusság" },
  ];

  const svg = await satori(
    {
      type: "div",
      props: {
        style: {
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#1c1c1c",
          padding: "56px 64px",
        },
        children: [
          // Brand + date row
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "36px",
              },
              children: [
                {
                  type: "div",
                  props: {
                    style: {
                      fontSize: 20,
                      fontFamily: "Playfair Display",
                      fontWeight: 700,
                      color: "#e8624e",
                      letterSpacing: "3px",
                    },
                    children: "HANGNEM",
                  },
                },
                {
                  type: "div",
                  props: {
                    style: {
                      fontSize: 16,
                      fontFamily: "Source Sans 3",
                      color: "#555",
                      letterSpacing: "1px",
                    },
                    children: conf.meta.date,
                  },
                },
              ],
            },
          },
          // Title
          {
            type: "div",
            props: {
              style: {
                fontSize: 46,
                fontFamily: "Playfair Display",
                fontWeight: 700,
                color: "#ffffff",
                lineHeight: 1.25,
                flex: 1,
              },
              children: conf.meta.title,
            },
          },
          // Stats row
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                flexDirection: "row",
                borderTop: "1px solid rgba(255,255,255,0.08)",
                paddingTop: "28px",
                gap: "0px",
              },
              children: stats.map((s) => ({
                type: "div",
                props: {
                  style: {
                    display: "flex",
                    flexDirection: "column",
                    flex: 1,
                  },
                  children: [
                    {
                      type: "div",
                      props: {
                        style: {
                          fontSize: 34,
                          fontFamily: "Playfair Display",
                          fontWeight: 700,
                          color: "#e8624e",
                          lineHeight: 1,
                        },
                        children: s.value,
                      },
                    },
                    {
                      type: "div",
                      props: {
                        style: {
                          fontSize: 12,
                          fontFamily: "Source Sans 3",
                          color: "#777",
                          marginTop: "6px",
                          letterSpacing: "0.5px",
                        },
                        children: s.label,
                      },
                    },
                  ],
                },
              })),
            },
          },
        ],
      },
    },
    {
      width: 1200,
      height: 630,
      fonts: [
        { name: "Playfair Display", data: playfair, weight: 700, style: "normal" },
        { name: "Source Sans 3", data: sourceSans, weight: 400, style: "normal" },
      ],
    }
  );

  const png = new Resvg(svg).render().asPng();
  return new Response(png, { headers: { "Content-Type": "image/png" } });
};
