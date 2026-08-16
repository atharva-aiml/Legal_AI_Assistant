import { defineConfig } from "drizzle-kit";
import * as fs from "node:fs";

// drizzle-kit doesn't auto-load .env.local; do it manually.
const envLocal = fs.readFileSync(".env.local", "utf-8");
for (const line of envLocal.split("\n")) {
  const match = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (match && !process.env[match[1]]) process.env[match[1]] = match[2];
}

export default defineConfig({
  schema: "./schema/schema.ts",
  out: "./migrations",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
