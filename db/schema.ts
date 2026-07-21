import { integer, real, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const users = sqliteTable("site_users", {
  email: text("email").primaryKey(),
  displayName: text("display_name").notNull(),
  role: text("role").notNull().default("resident"),
  area: text("area").notNull().default("全园区"),
  skills: text("skills"),
  currentLoad: integer("current_load").notNull().default(0),
  maxLoad: integer("max_load").notNull().default(5),
  rating: real("rating").notNull().default(95),
  createdAt: text("created_at").notNull(),
});

export const workOrders = sqliteTable("site_work_orders", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  orderNo: text("order_no").notNull().unique(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  category: text("category").notNull(),
  priority: text("priority").notNull(),
  status: text("status").notNull(),
  area: text("area").notNull(),
  reporterEmail: text("reporter_email").notNull(),
  reporterName: text("reporter_name").notNull(),
  assigneeEmail: text("assignee_email"),
  assigneeName: text("assignee_name"),
  summary: text("summary").notNull(),
  confidence: real("confidence").notNull().default(0.9),
  rating: real("rating"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const attachments = sqliteTable("site_attachments", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  ownerEmail: text("owner_email").notNull(),
  workOrderId: integer("work_order_id"),
  objectKey: text("object_key").notNull().unique(),
  originalName: text("original_name").notNull(),
  contentType: text("content_type").notNull(),
  mediaType: text("media_type").notNull(),
  sizeBytes: integer("size_bytes").notNull(),
  analysis: text("analysis"),
  createdAt: text("created_at").notNull(),
});

export const events = sqliteTable("site_order_events", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  workOrderId: integer("work_order_id").notNull(),
  actorEmail: text("actor_email").notNull(),
  action: text("action").notNull(),
  detail: text("detail").notNull(),
  createdAt: text("created_at").notNull(),
});
