ALTER TABLE "citations" ADD COLUMN "section" text;--> statement-breakpoint
ALTER TABLE "document_chunks" ADD COLUMN "section" text;--> statement-breakpoint
ALTER TABLE "document_chunks" ADD COLUMN "chunk_type" text DEFAULT 'prose' NOT NULL;