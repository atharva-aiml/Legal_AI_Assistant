import { cookies } from "next/headers";

const JAVA_API_URL = process.env.JAVA_API_URL ?? "http://localhost:8080";

/**
 * Server-side fetch to the Java backend — for Server Components and Route
 * Handlers. Unlike same-origin API routes, a cross-service call from
 * Next.js's own server doesn't automatically carry the browser's cookie,
 * so it's read explicitly and forwarded (System Architecture §5, step 5a-5b).
 */
export async function javaFetch(path: string, init?: RequestInit): Promise<Response> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  return fetch(`${JAVA_API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(cookieHeader ? { Cookie: cookieHeader } : {}),
    },
    cache: "no-store",
  });
}

export { JAVA_API_URL };
