// Safe to import from "use client" components — NEXT_PUBLIC_ vars are
// inlined at build time, unlike lib/api/java-client.ts which uses
// next/headers and is server-only.
export const JAVA_API_URL_PUBLIC = process.env.NEXT_PUBLIC_JAVA_API_URL ?? "http://localhost:8080";
