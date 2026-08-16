import { test, expect, request as playwrightRequest } from "@playwright/test";
import path from "node:path";

const JAVA_API_URL = "http://localhost:8080";

/**
 * Reproduces the exact bug report: upload a real document and confirm its
 * status badge moves from Processing to Ready IN PLACE — no page.reload()
 * is ever called in this test, so if the badge updates, it's the app's
 * own polling (documents-list.tsx) doing it, not a manual refresh.
 */
test("document status badge updates from Processing to Ready without a manual page reload", async ({ page }) => {
  const apiContext = await playwrightRequest.newContext({ baseURL: JAVA_API_URL });

  const uniqueEmail = `e2e-poll-${Date.now()}@example.com`;
  const registerRes = await apiContext.post("/api/auth/register", {
    data: { name: "E2E Polling Test", email: uniqueEmail, password: "correct-horse-battery" },
  });
  expect(registerRes.ok()).toBeTruthy();

  const cookies = await apiContext.storageState();
  const sessionCookie = cookies.cookies.find((c) => c.name === "session");
  expect(sessionCookie).toBeTruthy();

  const clientRes = await apiContext.post("/api/clients", { data: { name: "E2E Polling Client" } });
  const client = await clientRes.json();

  const matterRes = await apiContext.post("/api/matters", {
    data: { client_id: client.id, title: "E2E Polling Matter" },
  });
  const matter = await matterRes.json();

  // Give the browser the same session the API context authenticated with.
  await page.context().addCookies([
    {
      name: "session",
      value: sessionCookie!.value,
      domain: "localhost",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  await page.goto(`/matters/${matter.id}`);
  await expect(page.getByText("E2E Polling Matter")).toBeVisible();

  const fileInput = page.locator("#document-upload-input");
  await fileInput.setInputFiles(path.join(__dirname, "fixtures", "sample.pdf"));

  // Right after upload, Java has set it to 'processing' by the time the
  // upload response returns (DocumentService.upload) — this should show
  // up without any reload since DocumentUpload calls router.refresh().
  await expect(page.getByText("Processing")).toBeVisible({ timeout: 10000 });

  // The real fix under test: wait for it to become Ready via polling
  // alone. No page.reload() call anywhere in this test.
  await expect(page.getByText("Ready")).toBeVisible({ timeout: 20000 });

  // And Processing should be gone — confirms it's the same badge
  // transitioning, not a second document appearing.
  await expect(page.getByText("Processing")).not.toBeVisible();
});
