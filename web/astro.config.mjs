import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// Sitio estático: cada página se genera una sola vez al compilar y se sirve
// como HTML plano. Los gráficos son islas React que se cargan sólo donde
// hacen falta, así una página de tablas no descarga Recharts.
export default defineConfig({
  site: 'https://taxar.ar',
  integrations: [react()],
  build: { inlineStylesheets: 'auto' },
});
