CREATE TABLE `site_attachments` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`owner_email` text NOT NULL,
	`work_order_id` integer,
	`object_key` text NOT NULL,
	`original_name` text NOT NULL,
	`content_type` text NOT NULL,
	`media_type` text NOT NULL,
	`size_bytes` integer NOT NULL,
	`analysis` text,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `site_attachments_object_key_unique` ON `site_attachments` (`object_key`);--> statement-breakpoint
CREATE TABLE `site_order_events` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`work_order_id` integer NOT NULL,
	`actor_email` text NOT NULL,
	`action` text NOT NULL,
	`detail` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `site_users` (
	`email` text PRIMARY KEY NOT NULL,
	`display_name` text NOT NULL,
	`role` text DEFAULT 'resident' NOT NULL,
	`area` text DEFAULT '全园区' NOT NULL,
	`skills` text,
	`current_load` integer DEFAULT 0 NOT NULL,
	`max_load` integer DEFAULT 5 NOT NULL,
	`rating` real DEFAULT 95 NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `site_work_orders` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`order_no` text NOT NULL,
	`title` text NOT NULL,
	`description` text NOT NULL,
	`category` text NOT NULL,
	`priority` text NOT NULL,
	`status` text NOT NULL,
	`area` text NOT NULL,
	`reporter_email` text NOT NULL,
	`reporter_name` text NOT NULL,
	`assignee_email` text,
	`assignee_name` text,
	`summary` text NOT NULL,
	`confidence` real DEFAULT 0.9 NOT NULL,
	`rating` real,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `site_work_orders_order_no_unique` ON `site_work_orders` (`order_no`);