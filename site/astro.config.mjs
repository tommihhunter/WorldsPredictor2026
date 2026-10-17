// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  // W26_SITE_URL / W26_BASE switch the build to a custom domain (set in the workflows at cutover)
  site: process.env.W26_SITE_URL ?? 'https://poroprophet.lol',
  base: process.env.W26_BASE ?? '/',
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory' },
});
