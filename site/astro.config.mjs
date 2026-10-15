// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://tommihhunter.github.io',
  base: '/WorldsPredictor2026',
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory' },
});
