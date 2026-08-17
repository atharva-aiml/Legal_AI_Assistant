CREATE TYPE "public"."deadline_priority" AS ENUM('standard', 'critical');--> statement-breakpoint
ALTER TABLE "deadlines" ADD COLUMN "priority" "deadline_priority" DEFAULT 'standard' NOT NULL;