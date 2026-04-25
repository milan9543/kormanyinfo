// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: "https://hangnem.cc",
  integrations: [sitemap({ filter: (page) => !page.includes("/og/") })],
  vite: {
    plugins: [tailwindcss()]
  }
});