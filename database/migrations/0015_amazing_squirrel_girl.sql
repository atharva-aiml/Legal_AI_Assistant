ALTER TABLE "chat_messages" ADD COLUMN "parent_id" uuid;--> statement-breakpoint
ALTER TABLE "chat_messages" ADD COLUMN "active_child_id" uuid;--> statement-breakpoint
ALTER TABLE "matters" ADD COLUMN "active_root_message_id" uuid;--> statement-breakpoint
ALTER TABLE "chat_messages" ADD CONSTRAINT "chat_messages_parent_id_chat_messages_id_fk" FOREIGN KEY ("parent_id") REFERENCES "public"."chat_messages"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chat_messages" ADD CONSTRAINT "chat_messages_active_child_id_chat_messages_id_fk" FOREIGN KEY ("active_child_id") REFERENCES "public"."chat_messages"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "matters" ADD CONSTRAINT "matters_active_root_message_id_chat_messages_id_fk" FOREIGN KEY ("active_root_message_id") REFERENCES "public"."chat_messages"("id") ON DELETE set null ON UPDATE no action;