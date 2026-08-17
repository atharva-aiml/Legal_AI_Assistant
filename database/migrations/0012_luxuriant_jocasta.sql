CREATE TABLE "lawyer_preferences" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lawyer_id" uuid NOT NULL,
	"deadline_reminders_enabled" boolean DEFAULT true NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "lawyer_preferences" ADD CONSTRAINT "lawyer_preferences_lawyer_id_lawyers_id_fk" FOREIGN KEY ("lawyer_id") REFERENCES "public"."lawyers"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "lawyer_preferences_lawyer_unique" ON "lawyer_preferences" USING btree ("lawyer_id");