import { defineConfig } from "openapi-typescript";

// Generates src/lib/api-types.gen.ts from src/backend/openapi.json.
// Regenerate after any backend contract change:
//   1. uvicorn running  →  curl -s http://localhost:8000/openapi.json -o ../backend/openapi.json
//   2. npm run gen:api
// CI regenerates and fails on diff (drift tripwire), so schemas.ts cannot silently diverge.
export default defineConfig({
  petstore: {
    input: "../backend/openapi.json",
    output: "./src/lib/api-types.gen.ts",
  },
});
