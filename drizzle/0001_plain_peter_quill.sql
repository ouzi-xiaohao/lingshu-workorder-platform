CREATE TABLE `site_worker_performance` (
	`worker_email` text PRIMARY KEY NOT NULL,
	`credit_points` integer DEFAULT 1000 NOT NULL,
	`completed_orders` integer DEFAULT 0 NOT NULL,
	`on_time_rate` real DEFAULT 98 NOT NULL,
	`satisfaction` real DEFAULT 4.8 NOT NULL,
	`updated_at` text NOT NULL
);
