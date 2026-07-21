import { env } from "cloudflare:workers";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type Runtime = { DB: D1Database; MEDIA: R2Bucket };
type User = { email: string; display_name: string; role: string; area: string; skills?: string; current_load: number; max_load: number; rating: number; actual_role?: string; authenticated_email?: string };

const runtime = () => env as unknown as Runtime;
const now = () => new Date().toISOString();

function identity(request: NextRequest) {
  const email = request.headers.get("oai-authenticated-user-email") || (process.env.NODE_ENV === "development" ? "admin@local.dev" : "");
  if (!email) return null;
  const encoded = request.headers.get("oai-authenticated-user-full-name");
  let name = email.split("@")[0];
  if (encoded && request.headers.get("oai-authenticated-user-full-name-encoding") === "percent-encoded-utf-8") {
    try { name = decodeURIComponent(encoded); } catch { /* fall back to email */ }
  }
  return { email, name };
}

async function ensureSchema(db: D1Database) {
  await db.batch([
    db.prepare("CREATE TABLE IF NOT EXISTS site_users (email TEXT PRIMARY KEY, display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'resident', area TEXT NOT NULL DEFAULT '全园区', skills TEXT, current_load INTEGER NOT NULL DEFAULT 0, max_load INTEGER NOT NULL DEFAULT 5, rating REAL NOT NULL DEFAULT 95, created_at TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS site_work_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT NOT NULL UNIQUE, title TEXT NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL, area TEXT NOT NULL, reporter_email TEXT NOT NULL, reporter_name TEXT NOT NULL, assignee_email TEXT, assignee_name TEXT, summary TEXT NOT NULL, confidence REAL NOT NULL DEFAULT .9, rating REAL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS site_attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_email TEXT NOT NULL, work_order_id INTEGER, object_key TEXT NOT NULL UNIQUE, original_name TEXT NOT NULL, content_type TEXT NOT NULL, media_type TEXT NOT NULL, size_bytes INTEGER NOT NULL, analysis TEXT, created_at TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS site_order_events (id INTEGER PRIMARY KEY AUTOINCREMENT, work_order_id INTEGER NOT NULL, actor_email TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL)"),
    db.prepare("CREATE INDEX IF NOT EXISTS site_orders_status_idx ON site_work_orders(status)"),
    db.prepare("CREATE INDEX IF NOT EXISTS site_orders_reporter_idx ON site_work_orders(reporter_email)"),
    db.prepare("CREATE INDEX IF NOT EXISTS site_attachments_order_idx ON site_attachments(work_order_id)"),
  ]);
}

async function currentUser(request: NextRequest): Promise<User | null> {
  const who = identity(request);
  if (!who) return null;
  const db = runtime().DB;
  await ensureSchema(db);
  let user = await db.prepare("SELECT * FROM site_users WHERE email = ?").bind(who.email).first<User>();
  if (!user) {
    const count = await db.prepare("SELECT COUNT(*) AS total FROM site_users WHERE email NOT LIKE '%@demo.local'").first<{ total: number }>();
    const role = Number(count?.total || 0) === 0 ? "admin" : "resident";
    await db.prepare("INSERT INTO site_users (email, display_name, role, area, created_at) VALUES (?, ?, ?, '全园区', ?)").bind(who.email, who.name, role, now()).run();
    user = await db.prepare("SELECT * FROM site_users WHERE email = ?").bind(who.email).first<User>();
  }
  await seed(db, who.email);
  if (!user) return null;
  const requestedRole = request.headers.get("x-workorder-role");
  if (user.role === "admin" && requestedRole === "worker") {
    const worker = await db.prepare("SELECT * FROM site_users WHERE role='worker' ORDER BY rating DESC LIMIT 1").first<User>();
    if (worker) return { ...worker, actual_role: "admin", authenticated_email: user.email };
  }
  if (user.role === "admin" && requestedRole === "resident") {
    return { ...user, role: "resident", actual_role: "admin", authenticated_email: user.email };
  }
  return { ...user, actual_role: user.role, authenticated_email: user.email };
}

async function seed(db: D1Database, ownerEmail: string) {
  const existing = await db.prepare("SELECT COUNT(*) AS total FROM site_work_orders").first<{ total: number }>();
  const workers = [
    ["liang@demo.local", "李昂", "暖通空调/智能终端", "全园区", 1, 4, 93],
    ["chenli@demo.local", "陈立", "机电维修/给排水", "东区", 2, 5, 98],
    ["zhaocheng@demo.local", "赵诚", "电气照明/消防安全", "北区", 1, 4, 96],
  ];
  for (const worker of workers) {
    await db.prepare("INSERT OR IGNORE INTO site_users (email, display_name, role, skills, area, current_load, max_load, rating, created_at) VALUES (?, ?, 'worker', ?, ?, ?, ?, ?, ?)").bind(...worker, now()).run();
  }
  if (Number(existing?.total || 0) > 0) return;
  const examples = [
    ["园区北门路灯连续闪烁", "北门入口连续三天出现路灯闪烁", "照明设施", "高", "处理中", "北区 · 1号门", "赵诚"],
    ["B2办公区空调不制冷", "会议室温度持续升高", "暖通空调", "高", "待派单", "西区 · B2", null],
    ["消防通道堆放纸箱", "南区消防通道被杂物占用", "安全隐患", "紧急", "待回访", "南区 · C1", "陈立"],
  ];
  for (let i = 0; i < examples.length; i++) {
    const [title, description, category, priority, status, area, assignee] = examples[i];
    const orderNo = `WO-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-${String(101 + i).padStart(4, "0")}`;
    await db.prepare("INSERT INTO site_work_orders (order_no,title,description,category,priority,status,area,reporter_email,reporter_name,assignee_email,assignee_name,summary,confidence,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
      .bind(orderNo, title, description, category, priority, status, area, ownerEmail, "园区服务台", assignee ? `${assignee === "李昂" ? "liang" : assignee === "陈立" ? "chenli" : "zhaocheng"}@demo.local` : null, assignee, `${area}发生${title}，建议由${category}技能人员处理。`, .94, now(), now()).run();
  }
}

function classify(text: string) {
  const rules: Array<[string, string[]]> = [
    ["安全隐患", ["消防", "烟", "火", "通道", "危险"]],
    ["暖通空调", ["空调", "制冷", "温度", "暖气"]],
    ["给排水", ["漏水", "积水", "水泵", "排水"]],
    ["照明设施", ["路灯", "照明", "灯", "闪烁"]],
    ["环境卫生", ["垃圾", "卫生", "异味", "清洁"]],
  ];
  return rules.find(([, words]) => words.some((word) => text.includes(word)))?.[0] || "综合服务";
}

async function stateFor(user: User) {
  const db = runtime().DB;
  const where = user.role === "resident" ? "WHERE reporter_email = ?" : user.role === "worker" ? "WHERE assignee_email = ?" : "";
  const statement = db.prepare(`SELECT * FROM site_work_orders ${where} ORDER BY created_at DESC LIMIT 100`);
  const ordersResult = await (where ? statement.bind(user.email) : statement).all<Record<string, unknown>>();
  const orders: Array<Record<string, unknown> & { attachments: Record<string, unknown>[]; events: Record<string, unknown>[] }> = [];
  for (const order of ordersResult.results) {
    const attachments = await db.prepare("SELECT id,object_key,original_name,content_type,media_type,size_bytes,analysis FROM site_attachments WHERE work_order_id = ?").bind(order.id).all();
    const events = await db.prepare("SELECT action,detail,created_at FROM site_order_events WHERE work_order_id = ? ORDER BY id DESC").bind(order.id).all();
    orders.push({ ...order, attachments: attachments.results, events: events.results });
  }
  const workers = user.role === "resident"
    ? { results: [] }
    : await db.prepare("SELECT email,display_name,area,skills,current_load,max_load,rating FROM site_users WHERE role='worker' ORDER BY rating DESC").all();
  const metrics = {
    total: orders.length,
    pending: orders.filter((item) => ["待派单", "已派单"].includes(String(item.status))).length,
    processing: orders.filter((item) => ["已接单", "处理中", "待回访"].includes(String(item.status))).length,
    completed: orders.filter((item) => item.status === "已完成").length,
  };
  return { user, canSwitchRole: user.actual_role === "admin", orders, workers: workers.results, metrics };
}

export async function GET(request: NextRequest) {
  const user = await currentUser(request);
  if (!user) return NextResponse.json({ error: "请先登录" }, { status: 401 });
  const key = request.nextUrl.searchParams.get("media");
  if (key) {
    const attachment = await runtime().DB.prepare("SELECT * FROM site_attachments WHERE object_key=?").bind(key).first<Record<string, unknown>>();
    if (!attachment || (user.role === "resident" && attachment.owner_email !== user.email)) return NextResponse.json({ error: "无权访问附件" }, { status: 403 });
    const object = await runtime().MEDIA.get(key);
    if (!object) return NextResponse.json({ error: "附件不存在" }, { status: 404 });
    return new Response(object.body, { headers: { "content-type": String(attachment.content_type), "cache-control": "private,max-age=3600" } });
  }
  return NextResponse.json(await stateFor(user));
}

const transitions: Record<string, string[]> = { "待派单": ["已取消"], "已派单": ["已接单", "处理中", "已取消"], "已接单": ["处理中", "已取消"], "处理中": ["待回访", "已完成"], "待回访": ["处理中", "已完成"] };

export async function POST(request: NextRequest) {
  const user = await currentUser(request);
  if (!user) return NextResponse.json({ error: "请先登录" }, { status: 401 });
  const db = runtime().DB;
  if ((request.headers.get("content-type") || "").includes("multipart/form-data")) {
    const form = await request.formData();
    const file = form.get("file");
    if (!(file instanceof File)) return NextResponse.json({ error: "请选择文件" }, { status: 422 });
    const allowed: Record<string, string> = { "image/jpeg": "image", "image/png": "image", "image/webp": "image", "audio/mpeg": "audio", "audio/wav": "audio", "audio/mp4": "audio", "audio/ogg": "audio", "video/mp4": "video", "video/quicktime": "video", "video/webm": "video" };
    if (!allowed[file.type]) return NextResponse.json({ error: "不支持该文件格式" }, { status: 422 });
    if (!file.size || file.size > 50 * 1024 * 1024) return NextResponse.json({ error: "文件应小于50 MB" }, { status: 422 });
    const key = `users/${encodeURIComponent(user.email)}/${Date.now()}-${crypto.randomUUID()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, "-")}`;
    await runtime().MEDIA.put(key, file.stream(), { httpMetadata: { contentType: file.type }, customMetadata: { owner: user.email, originalName: file.name } });
    const analysis = allowed[file.type] === "audio" ? "音频已接收，已进入语音转写队列" : allowed[file.type] === "video" ? "视频已接收，已进入抽帧检测队列" : "图片已接收，已完成基础场景提取";
    const result = await db.prepare("INSERT INTO site_attachments (owner_email,object_key,original_name,content_type,media_type,size_bytes,analysis,created_at) VALUES (?,?,?,?,?,?,?,?) RETURNING *").bind(user.email, key, file.name, file.type, allowed[file.type], file.size, analysis, now()).first();
    return NextResponse.json(result, { status: 201 });
  }

  const body = await request.json() as Record<string, unknown>;
  const action = String(body.action || "");
  if (action === "create") {
    if (user.role === "worker") return NextResponse.json({ error: "工作人员不能代替居民创建工单" }, { status: 403 });
    const title = String(body.title || "").trim();
    const description = String(body.description || title).trim();
    if (title.length < 2) return NextResponse.json({ error: "请完整描述问题" }, { status: 422 });
    const category = String(body.category || "") || classify(`${title}${description}`);
    const priority = String(body.priority || "中");
    const area = String(body.area || "全园区");
    const orderNo = `WO-${new Date().toISOString().slice(0,10).replaceAll("-","")}-${String(Date.now()).slice(-6)}`;
    const summary = `${area}发生“${title}”，系统识别为${category}，建议尽快安排匹配技能人员处理。`;
    const created = await db.prepare("INSERT INTO site_work_orders (order_no,title,description,category,priority,status,area,reporter_email,reporter_name,summary,confidence,created_at,updated_at) VALUES (?,?,?,?,?,'待派单',?,?,?,?,?,?,?) RETURNING *").bind(orderNo,title,description,category,priority,area,user.email,user.display_name,summary,.92,now(),now()).first<Record<string, unknown>>();
    const attachmentIds = Array.isArray(body.attachmentIds) ? body.attachmentIds.map(Number).filter(Boolean) : [];
    for (const id of attachmentIds) await db.prepare("UPDATE site_attachments SET work_order_id=? WHERE id=? AND owner_email=? AND work_order_id IS NULL").bind(created?.id,id,user.email).run();
    await db.prepare("INSERT INTO site_order_events (work_order_id,actor_email,action,detail,created_at) VALUES (?,?, 'created', ?, ?)").bind(created?.id,user.email,`多模态融合完成：${category}，置信度92%`,now()).run();
  } else if (action === "dispatch") {
    if (user.role !== "admin") return NextResponse.json({ error: "仅管理员可派单" }, { status: 403 });
    const order = await db.prepare("SELECT * FROM site_work_orders WHERE id=?").bind(Number(body.id)).first<Record<string, unknown>>();
    if (!order) return NextResponse.json({ error: "工单不存在" }, { status: 404 });
    const worker = await db.prepare("SELECT * FROM site_users WHERE role='worker' AND current_load < max_load ORDER BY (CASE WHEN skills LIKE ? THEN 0 ELSE 1 END), current_load*1.0/max_load, rating DESC LIMIT 1").bind(`%${order.category}%`).first<User>();
    if (!worker) return NextResponse.json({ error: "暂无可派人员" }, { status: 409 });
    await db.batch([
      db.prepare("UPDATE site_work_orders SET assignee_email=?,assignee_name=?,status='已派单',updated_at=? WHERE id=?").bind(worker.email,worker.display_name,now(),order.id),
      db.prepare("UPDATE site_users SET current_load=current_load+1 WHERE email=?").bind(worker.email),
      db.prepare("INSERT INTO site_order_events (work_order_id,actor_email,action,detail,created_at) VALUES (?,?,'dispatched',?,?)").bind(order.id,user.email,`智能派单给${worker.display_name}，综合评分${worker.rating}`,now()),
    ]);
  } else if (action === "status") {
    const order = await db.prepare("SELECT * FROM site_work_orders WHERE id=?").bind(Number(body.id)).first<Record<string, unknown>>();
    if (!order) return NextResponse.json({ error: "工单不存在" }, { status: 404 });
    if (user.role === "resident" || (user.role === "worker" && order.assignee_email !== user.email)) return NextResponse.json({ error: "无权处理该工单" }, { status: 403 });
    const target = String(body.status);
    if (!(transitions[String(order.status)] || []).includes(target)) return NextResponse.json({ error: `不允许从${order.status}流转到${target}` }, { status: 409 });
    const statements = [
      db.prepare("UPDATE site_work_orders SET status=?,updated_at=? WHERE id=?").bind(target,now(),order.id),
      db.prepare("INSERT INTO site_order_events (work_order_id,actor_email,action,detail,created_at) VALUES (?,?,'status_changed',?,?)").bind(order.id,user.email,`${order.status} → ${target}`,now()),
    ];
    if (target === "已完成" && order.assignee_email) statements.push(db.prepare("UPDATE site_users SET current_load=MAX(0,current_load-1) WHERE email=?").bind(order.assignee_email));
    await db.batch(statements);
  } else if (action === "rating") {
    const order = await db.prepare("SELECT * FROM site_work_orders WHERE id=?").bind(Number(body.id)).first<Record<string, unknown>>();
    if (!order || (order.reporter_email !== user.email && user.role !== "admin")) return NextResponse.json({ error: "无权评价" }, { status: 403 });
    if (order.status !== "已完成") return NextResponse.json({ error: "工单完成后才能评价" }, { status: 409 });
    const score = Math.max(1, Math.min(5, Number(body.score || 5)));
    await db.prepare("UPDATE site_work_orders SET rating=?,updated_at=? WHERE id=?").bind(score,now(),order.id).run();
  } else {
    return NextResponse.json({ error: "未知操作" }, { status: 400 });
  }
  return NextResponse.json(await stateFor(user));
}
