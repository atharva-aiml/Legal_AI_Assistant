import { pgTable, uuid, text, timestamp, date, pgEnum, integer, bigint, boolean, customType } from "drizzle-orm/pg-core";

// Drizzle has no built-in pgvector column type (CLAUDE.md §4) — defined via
// customType, fixed at 384 dimensions to match all-MiniLM-L6-v2 (System
// Architecture §6).
const vector384 = customType<{ data: number[]; driverData: string }>({
  dataType() {
    return "vector(384)";
  },
  toDriver(value: number[]): string {
    return `[${value.join(",")}]`;
  },
  fromDriver(value: string): number[] {
    return value
      .slice(1, -1)
      .split(",")
      .map(Number);
  },
});

// V0.1 walking skeleton: only the tables needed for real auth + the Client
// round trip (System Architecture §3). Matter/Document/Deadline/etc. are
// added in their own Build Plan versions, not here.

export const lawyerRoleEnum = pgEnum("lawyer_role", ["owner", "member"]);

export const firms = pgTable("firms", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: text("name").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const lawyers = pgTable("lawyers", {
  id: uuid("id").primaryKey().defaultRandom(),
  firmId: uuid("firm_id")
    .notNull()
    .references(() => firms.id),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  passwordHash: text("password_hash").notNull(), // bcrypt, cost 12 — never returned by any API response
  role: lawyerRoleEnum("role").notNull().default("owner"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const sessions = pgTable("sessions", {
  id: uuid("id").primaryKey().defaultRandom(),
  lawyerId: uuid("lawyer_id")
    .notNull()
    .references(() => lawyers.id),
  tokenHash: text("token_hash").notNull().unique(), // SHA-256 of the raw cookie token
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const clients = pgTable("clients", {
  id: uuid("id").primaryKey().defaultRandom(),
  firmId: uuid("firm_id")
    .notNull()
    .references(() => firms.id), // BR-008: every tenant-owned row carries firm_id
  name: text("name").notNull(),
  contactEmail: text("contact_email"),
  contactPhone: text("contact_phone"),
  notes: text("notes"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const matterStatusEnum = pgEnum("matter_status", ["open", "closed"]);

export const matters = pgTable("matters", {
  id: uuid("id").primaryKey().defaultRandom(),
  firmId: uuid("firm_id")
    .notNull()
    .references(() => firms.id), // BR-008
  clientId: uuid("client_id")
    .notNull()
    .references(() => clients.id), // BR-001
  title: text("title").notNull(),
  status: matterStatusEnum("status").notNull().default("open"), // BR-003 (enforced from V0.5)
  closedAt: timestamp("closed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

// SD-007: firmId nullable — null = system template (available to every
// Firm), set = Firm-custom (visible only to that Firm). V0.8 doesn't build
// a template-authoring UI (System Architecture: "does not create templates
// from user free text — templates are pre-authored"), so firm-custom rows
// aren't populated by any code path yet, only system templates via a seed.
export const templates = pgTable("templates", {
  id: uuid("id").primaryKey().defaultRandom(),
  firmId: uuid("firm_id").references(() => firms.id),
  name: text("name").notNull(),
  description: text("description"),
  body: text("body").notNull(), // placeholder-bearing template content, {{field_name}} syntax
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const documentStatusEnum = pgEnum("document_status", ["uploading", "processing", "ready", "failed"]);

export const documents = pgTable("documents", {
  id: uuid("id").primaryKey().defaultRandom(),
  matterId: uuid("matter_id")
    .notNull()
    .references(() => matters.id), // BR-002
  uploadedBy: uuid("uploaded_by")
    .notNull()
    .references(() => lawyers.id),
  fileName: text("file_name").notNull(),
  storageKey: text("storage_key").notNull(),
  mimeType: text("mime_type").notNull(),
  sizeBytes: bigint("size_bytes", { mode: "number" }).notNull(),
  status: documentStatusEnum("status").notNull().default("uploading"), // REQ-004
  isDraft: boolean("is_draft").notNull().default(false), // REQ-015, set true from V0.8
  sourceTemplateId: uuid("source_template_id").references(() => templates.id), // REQ-015, set from V0.8
  errorMessage: text("error_message"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const documentChunks = pgTable("document_chunks", {
  id: uuid("id").primaryKey().defaultRandom(),
  documentId: uuid("document_id")
    .notNull()
    .references(() => documents.id, { onDelete: "cascade" }), // REQ-027: deleting a Document cleans up its chunks at the DB level
  pageNumber: integer("page_number"),
  content: text("content").notNull(),
  embedding: vector384("embedding").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const deadlineStatusEnum = pgEnum("deadline_status", ["open", "complete"]);

export const deadlines = pgTable("deadlines", {
  id: uuid("id").primaryKey().defaultRandom(),
  matterId: uuid("matter_id")
    .notNull()
    .references(() => matters.id), // BR-004: a Deadline always has a linked Matter
  title: text("title").notNull(),
  dueDate: date("due_date").notNull(), // date, not timestamp — a Deadline is a calendar day, no time-of-day concept
  status: deadlineStatusEnum("status").notNull().default("open"), // BR-003
  notificationLeadDays: integer("notification_lead_days").notNull().default(3), // REQ-016
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const notifications = pgTable("notifications", {
  id: uuid("id").primaryKey().defaultRandom(),
  lawyerId: uuid("lawyer_id")
    .notNull()
    .references(() => lawyers.id), // recipient
  deadlineId: uuid("deadline_id")
    .notNull()
    .references(() => deadlines.id, { onDelete: "cascade" }), // a Notification can't outlive the Deadline it's about
  message: text("message").notNull(),
  sentAt: timestamp("sent_at", { withTimezone: true }),
  readAt: timestamp("read_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const chatRoleEnum = pgEnum("chat_role", ["user", "assistant"]);

export const chatMessages = pgTable("chat_messages", {
  id: uuid("id").primaryKey().defaultRandom(),
  matterId: uuid("matter_id")
    .notNull()
    .references(() => matters.id), // BR-005
  lawyerId: uuid("lawyer_id").references(() => lawyers.id), // null when role='assistant'
  role: chatRoleEnum("role").notNull(),
  content: text("content").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const citations = pgTable("citations", {
  id: uuid("id").primaryKey().defaultRandom(),
  chatMessageId: uuid("chat_message_id")
    .notNull()
    .references(() => chatMessages.id, { onDelete: "cascade" }), // a Citation can't outlive its ChatMessage
  // No ON DELETE CASCADE here, deliberately: AI Architecture §4 says citations
  // are "persisted permanently... never recomputed later" — REQ-027 lets a
  // lawyer delete a Document unconditionally, so a citation that outlives its
  // source Document keeps its row (and excerpt) as the historical record,
  // just with document_id nulled out rather than being deleted itself.
  documentId: uuid("document_id").references(() => documents.id, { onDelete: "set null" }),
  pageNumber: integer("page_number"),
  excerpt: text("excerpt"), // quoted snippet backing the claim (BR-006)
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export type Firm = typeof firms.$inferSelect;
export type Lawyer = typeof lawyers.$inferSelect;
export type Session = typeof sessions.$inferSelect;
export type Client = typeof clients.$inferSelect;
export type NewClient = typeof clients.$inferInsert;
export type MatterRow = typeof matters.$inferSelect;
export type DocumentRow = typeof documents.$inferSelect;
export type DocumentChunkRow = typeof documentChunks.$inferSelect;
export type ChatMessageRow = typeof chatMessages.$inferSelect;
export type CitationRow = typeof citations.$inferSelect;
export type DeadlineRow = typeof deadlines.$inferSelect;
export type NotificationRow = typeof notifications.$inferSelect;
export type TemplateRow = typeof templates.$inferSelect;
