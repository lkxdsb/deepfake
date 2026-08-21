# Lingmou Vue Frontend

Vue 3 single-page frontend for the Java business backend. It replaces the Jinja2 pages while the
Python application remains responsible only for model inference.

## Stack

- Vue 3 and TypeScript
- Vite
- Vue Router and Pinia
- Axios
- ECharts
- Lucide icons

## Development

Start the Java backend on port `8080`, then run:

```bash
cd web-frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api/**` and `/outputs/**` to Spring Boot.

## Production

Build the frontend before packaging or starting Spring Boot:

```bash
cd web-frontend
npm ci
npm run build

cd ../java-backend
mvn package
```

Maven copies `web-frontend/dist` into the Spring Boot static resources. Spring Boot also forwards
the Vue routes to `index.html`, so browser refreshes work on detection and history detail pages.
