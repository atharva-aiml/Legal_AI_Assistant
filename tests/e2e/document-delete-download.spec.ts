import { test, expect, request as playwrightRequest } from "@playwright/test";
import path from "node:path";

const JAVA_API_URL = "http://localhost:8080";

/**
 * Exercises the actual Download link and Delete button in documents-list.tsx
 * through a real browser — the backend (DELETE /api/documents/:id, download
 * byte-fidelity, cascade, cross-firm isolation) was already proven via curl;
 * this proves the UI wiring: button click -> confirm() -> fetch -> list update.
 */
test("lawyer can download and delete a document from the Matter detail page", async ({ page }) => {
  const apiContext = await playwrightRequest.newContext({ baseURL: JAVA_API_URL });

  const uniqueEmail = `e2e-delete-${Date.now()}@example.com`;
  const registerRes = await apiContext.post("/api/auth/register", {
    data: { name: "E2E Delete Test", email: uniqueEmail, password: "correct-horse-battery" },
  });
  expect(registerRes.ok()).toBeTruthy();

  const cookies = await apiContext.storageState();
  const sessionCookie = cookies.cookies.find((c) => c.name === "session");
  expect(sessionCookie).toBeTruthy();

  const clientRes = await apiContext.post("/api/clients", { data: { name: "E2E Delete Client" } });
  const client = await clientRes.json();

  const matterRes = await apiContext.post("/api/matters", {
    data: { client_id: client.id, title: "E2E Delete Matter" },
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
  await expect(page.getByText("E2E Delete Matter")).toBeVisible();

  const fileInput = page.locator("#document-upload-input");
  await fileInput.setInputFiles(path.join(__dirname, "fixtures", "sample.pdf"));
  await expect(page.getByText("Ready")).toBeVisible({ timeout: 20000 });

  // Download: click the link and confirm a real file comes back, not a 404/error page.
  const downloadPromise = page.waitForEvent("download");
  await page.getByText("Download").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("sample.pdf");

  // Delete: the button calls window.confirm() — accept it via the dialog handler.
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByText("Delete", { exact: true }).click();

  // The row (and its "Ready" badge / filename) disappears from the list without a reload.
  await expect(page.getByText("sample.pdf")).not.toBeVisible({ timeout: 10000 });
  await expect(page.getByText("No documents yet")).toBeVisible();
});

test("cancelling the delete confirmation leaves the document in place", async ({ page }) => {
  const apiContext = await playwrightRequest.newContext({ baseURL: JAVA_API_URL });

  const uniqueEmail = `e2e-delete-cancel-${Date.now()}@example.com`;
  const registerRes = await apiContext.post("/api/auth/register", {
    data: { name: "E2E Delete Cancel Test", email: uniqueEmail, password: "correct-horse-battery" },
  });
  expect(registerRes.ok()).toBeTruthy();

  const cookies = await apiContext.storageState();
  const sessionCookie = cookies.cookies.find((c) => c.name === "session");

  const clientRes = await apiContext.post("/api/clients", { data: { name: "E2E Delete Cancel Client" } });
  const client = await clientRes.json();

  const matterRes = await apiContext.post("/api/matters", {
    data: { client_id: client.id, title: "E2E Delete Cancel Matter" },
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
  await fileInput.setInputFiles(path.join(__dirname, "fixtures", "sample.pdf"));
  await expect(page.getByText("Ready")).toBeVisible({ timeout: 20000 });

  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByText("Delete", { exact: true }).click();

  // Dismissing the confirm must not delete anything — document stays visible.
  await page.waitForTimeout(1000);
  await expect(page.getByText("sample.pdf")).toBeVisible();
});
