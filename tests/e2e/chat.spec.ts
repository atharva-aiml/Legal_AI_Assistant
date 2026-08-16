import { test, expect, request as playwrightRequest } from "@playwright/test";
import path from "node:path";

const JAVA_API_URL = "http://localhost:8080";

/**
 * V0.4 live check: a lawyer asks a real question about an uploaded document
 * and gets back a cited answer, then reloads the page to prove the
 * conversation persisted server-side (Postgres via Python's chat_messages/
 * citations tables) rather than living only in React state.
 */
test("a lawyer can ask the Assistant a question and the answer + citation survive a reload", async ({ page }) => {
  const apiContext = await playwrightRequest.newContext({ baseURL: JAVA_API_URL });

  const uniqueEmail = `e2e-chat-${Date.now()}@example.com`;
  const registerRes = await apiContext.post("/api/auth/register", {
    data: { name: "E2E Chat Test", email: uniqueEmail, password: "correct-horse-battery" },
  });
  expect(registerRes.ok()).toBeTruthy();

  const cookies = await apiContext.storageState();
  const sessionCookie = cookies.cookies.find((c) => c.name === "session");
  expect(sessionCookie).toBeTruthy();

  const clientRes = await apiContext.post("/api/clients", { data: { name: "E2E Chat Client" } });
  const client = await clientRes.json();

  const matterRes = await apiContext.post("/api/matters", {
    data: { client_id: client.id, title: "E2E Chat Matter" },
  });
  const matter = await matterRes.json();

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
  await expect(page.getByText("E2E Chat Matter")).toBeVisible();

  // Before any Document is Ready, the Chat tab should say so rather than accepting a question.
  await expect(page.getByText("Upload a document first")).toBeVisible();

  const fileInput = page.locator("#document-upload-input");
  await fileInput.setInputFiles(path.join(__dirname, "fixtures", "lease_agreement.docx"));
  await expect(page.getByText("Ready")).toBeVisible({ timeout: 20000 });

  const questionBox = page.getByPlaceholder("Ask about this Matter's documents…");
  await expect(questionBox).toBeVisible({ timeout: 10000 });
  await questionBox.fill("What is the monthly rent?");
  await page.getByRole("button", { name: "Ask" }).click();

  // Real OpenAI call in flight — give it real time, not a UI-only timeout.
  await expect(page.getByText(/1,45,000/).first()).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole("link", { name: /lease_agreement\.docx/ })).toBeVisible();

  await page.reload();

  // Server-rendered from GET /api/matters/:id/chat — proves this is real
  // Postgres persistence, not React state that a reload would wipe out.
  await expect(page.getByText("What is the monthly rent?")).toBeVisible();
  await expect(page.getByText(/1,45,000/).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /lease_agreement\.docx/ })).toBeVisible();
});

test("a question with no supporting content gets the fixed not-found response, not a fabricated answer", async ({ page }) => {
  const apiContext = await playwrightRequest.newContext({ baseURL: JAVA_API_URL });

  const uniqueEmail = `e2e-chat-notfound-${Date.now()}@example.com`;
  const registerRes = await apiContext.post("/api/auth/register", {
    data: { name: "E2E Chat Not-Found Test", email: uniqueEmail, password: "correct-horse-battery" },
  });
  expect(registerRes.ok()).toBeTruthy();

  const cookies = await apiContext.storageState();
  const sessionCookie = cookies.cookies.find((c) => c.name === "session");

  const clientRes = await apiContext.post("/api/clients", { data: { name: "E2E Not-Found Client" } });
  const client = await clientRes.json();

  const matterRes = await apiContext.post("/api/matters", {
    data: { client_id: client.id, title: "E2E Not-Found Matter" },
  });
  const matter = await matterRes.json();

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
  const fileInput = page.locator("#document-upload-input");
  await fileInput.setInputFiles(path.join(__dirname, "fixtures", "lease_agreement.docx"));
  await expect(page.getByText("Ready")).toBeVisible({ timeout: 20000 });

  const questionBox = page.getByPlaceholder("Ask about this Matter's documents…");
  await questionBox.fill("What is the maximum penalty for insider trading under the SEBI Act?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("I couldn't find that in this Matter's documents.")).toBeVisible({ timeout: 20000 });
});
