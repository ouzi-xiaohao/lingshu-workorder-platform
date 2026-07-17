"use client";

import { useMemo, useState } from "react";

type Priority = "紧急" | "高" | "中" | "低";
type Status = "待识别" | "待派单" | "处理中" | "待回访" | "已完成";

type Ticket = {
  id: string;
  title: string;
  category: string;
  area: string;
  reporter: string;
  assignee: string;
  priority: Priority;
  status: Status;
  created: string;
  sla: string;
  media: string[];
  confidence: number;
};

const initialTickets: Ticket[] = [
  { id: "WO-20260717-0842", title: "A3 栋地下车库排水泵异响", category: "设备故障", area: "东区 · A3", reporter: "林女士", assignee: "陈立", priority: "紧急", status: "处理中", created: "09:42", sla: "00:38", media: ["图片", "语音"], confidence: 96 },
  { id: "WO-20260717-0837", title: "园区北门路灯连续闪烁", category: "照明设施", area: "北区 · 1 号门", reporter: "周先生", assignee: "赵诚", priority: "高", status: "处理中", created: "09:31", sla: "01:12", media: ["视频"], confidence: 94 },
  { id: "WO-20260717-0831", title: "B2 办公区空调不制冷", category: "暖通空调", area: "西区 · B2", reporter: "前台服务", assignee: "待分配", priority: "高", status: "待派单", created: "09:18", sla: "00:26", media: ["文字", "图片"], confidence: 91 },
  { id: "WO-20260717-0825", title: "访客中心遗失黑色双肩包", category: "失物招领", area: "中心区", reporter: "何女士", assignee: "吴梅", priority: "中", status: "待回访", created: "08:56", sla: "03:44", media: ["文字"], confidence: 88 },
  { id: "WO-20260717-0819", title: "消防通道堆放纸箱", category: "安全隐患", area: "南区 · C1", reporter: "巡检 Agent", assignee: "孙航", priority: "高", status: "处理中", created: "08:41", sla: "01:05", media: ["图片"], confidence: 98 },
  { id: "WO-20260717-0808", title: "餐厅自助结算设备无法扫码", category: "终端设备", area: "生活区 · 食堂", reporter: "王师傅", assignee: "李昂", priority: "中", status: "已完成", created: "08:12", sla: "已按时", media: ["视频", "文字"], confidence: 93 },
];

const agents = [
  { name: "意图识别 Agent", detail: "分类 · 紧急度 · 标签", state: "运行中", metric: "96.4%", tone: "cyan" },
  { name: "智能调度 Agent", detail: "技能 · 距离 · 负载", state: "运行中", metric: "42 ms", tone: "lime" },
  { name: "流转监控 Agent", detail: "SLA · 改派 · 升级", state: "巡检中", metric: "12 项", tone: "violet" },
  { name: "积分结算 Agent", detail: "绩效 · 奖惩 · 权益", state: "待命", metric: "1,284", tone: "amber" },
];

const workers = [
  { name: "陈立", skill: "机电维修", zone: "东区", load: 3, max: 5, score: 98, state: "作业中" },
  { name: "赵诚", skill: "电气照明", zone: "北区", load: 2, max: 4, score: 96, state: "作业中" },
  { name: "孙航", skill: "消防安全", zone: "南区", load: 3, max: 4, score: 95, state: "作业中" },
  { name: "李昂", skill: "智能终端", zone: "中心区", load: 1, max: 4, score: 93, state: "可调度" },
  { name: "吴梅", skill: "综合服务", zone: "全园区", load: 2, max: 6, score: 91, state: "可调度" },
];

const navItems = ["指挥中心", "工单池", "智能体", "人员调度", "数据分析"];

function Icon({ name }: { name: string }) {
  const icons: Record<string, string> = { "指挥中心": "⌘", "工单池": "▤", "智能体": "✦", "人员调度": "◎", "数据分析": "⌁" };
  return <span className="nav-icon" aria-hidden="true">{icons[name]}</span>;
}

function Pill({ children, kind = "neutral" }: { children: React.ReactNode; kind?: string }) {
  return <span className={`pill pill-${kind}`}>{children}</span>;
}

export default function Home() {
  const [active, setActive] = useState("指挥中心");
  const [tickets, setTickets] = useState(initialTickets);
  const [selected, setSelected] = useState<Ticket>(initialTickets[2]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("全部状态");
  const [createOpen, setCreateOpen] = useState(false);
  const [toast, setToast] = useState("");

  const filtered = useMemo(() => tickets.filter((ticket) => {
    const matchesQuery = `${ticket.id}${ticket.title}${ticket.category}${ticket.area}`.toLowerCase().includes(query.toLowerCase());
    const matchesStatus = statusFilter === "全部状态" || ticket.status === statusFilter;
    return matchesQuery && matchesStatus;
  }), [tickets, query, statusFilter]);

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };

  const dispatchSelected = () => {
    const updated = { ...selected, assignee: "李昂", status: "处理中" as Status };
    setSelected(updated);
    setTickets((items) => items.map((item) => item.id === selected.id ? updated : item));
    notify("智能调度完成：已派发给李昂");
  };

  const addTicket = (form: FormData) => {
    const title = String(form.get("title") || "未命名工单");
    const ticket: Ticket = {
      id: `WO-20260717-${String(850 + tickets.length).padStart(4, "0")}`,
      title,
      category: String(form.get("category") || "待识别"),
      area: String(form.get("area") || "中心区"),
      reporter: "管理员创建",
      assignee: "待分配",
      priority: form.get("priority") as Priority || "中",
      status: "待识别",
      created: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
      sla: "00:30",
      media: ["文字", "附件"],
      confidence: 0,
    };
    setTickets((items) => [ticket, ...items]);
    setSelected(ticket);
    setCreateOpen(false);
    setActive("工单池");
    notify("工单已提交，AI 解析任务已进入队列");
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><span /></div>
          <div><strong>灵枢</strong><small>智能工单中枢</small></div>
        </div>
        <nav aria-label="主导航">
          {navItems.map((item) => (
            <button className={active === item ? "active" : ""} key={item} onClick={() => setActive(item)}>
              <Icon name={item} /><span>{item}</span>{item === "工单池" && <em>12</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-health"><span className="pulse" /><div><strong>系统运行正常</strong><small>5 个 Agent 在线</small></div></div>
          <button className="profile"><span className="avatar">林</span><span><strong>林悦</strong><small>运营管理员</small></span><b>•••</b></button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><p>园区运行中心</p><span className="crumb">/ {active}</span></div>
          <div className="top-actions">
            <label className="search"><span>⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索工单、人员或区域" /><kbd>⌘ K</kbd></label>
            <button className="icon-button" aria-label="消息通知">◔<i>3</i></button>
            <button className="primary" onClick={() => setCreateOpen(true)}>＋ 新建工单</button>
          </div>
        </header>

        {active === "指挥中心" && <Dashboard tickets={tickets} onOpen={(ticket) => { setSelected(ticket); setActive("工单池"); }} />}
        {active === "工单池" && <TicketPool filtered={filtered} selected={selected} setSelected={setSelected} query={query} setQuery={setQuery} statusFilter={statusFilter} setStatusFilter={setStatusFilter} onDispatch={dispatchSelected} />}
        {active === "智能体" && <AgentCenter />}
        {active === "人员调度" && <Workforce />}
        {active === "数据分析" && <Analytics />}
      </section>

      {createOpen && <CreateModal onClose={() => setCreateOpen(false)} onSubmit={addTicket} />}
      {toast && <div className="toast"><span>✓</span>{toast}</div>}
    </main>
  );
}

function Dashboard({ tickets, onOpen }: { tickets: Ticket[]; onOpen: (ticket: Ticket) => void }) {
  return <div className="page dashboard-page">
    <div className="page-heading"><div><Pill kind="live"><span className="pulse" /> 实时运行</Pill><h1>上午好，林悦</h1><p>当前有 <strong>12</strong> 张工单需要关注，3 张即将触发 SLA 预警。</p></div><div className="date-card"><span>07</span><div><b>星期五</b><small>2026 年 7 月 17 日</small></div></div></div>
    <section className="metrics-grid">
      <Metric title="今日工单" value="284" change="12.8%" note="较昨日" tone="cyan" chart={[20, 30, 26, 41, 38, 51, 49, 67]} />
      <Metric title="处理中" value="68" change="8.2%" note="平均用时 1.4h" tone="violet" chart={[44, 38, 49, 31, 54, 47, 59, 54]} />
      <Metric title="按时完成率" value="96.8%" change="2.1%" note="目标 95%" tone="lime" chart={[35, 42, 46, 50, 54, 61, 64, 70]} />
      <Metric title="智能派单率" value="92.4%" change="4.6%" note="人工干预 21 单" tone="amber" chart={[26, 36, 33, 50, 44, 55, 63, 68]} />
    </section>
    <section className="dashboard-grid">
      <div className="panel flow-panel"><PanelTitle title="智能调度流水线" subtitle="最近 30 分钟处理 86 个任务" action="查看日志" />
        <div className="agent-flow">
          {agents.map((agent, index) => <div className={`agent-node ${agent.tone}`} key={agent.name}><div className="agent-symbol">{index === 0 ? "⌁" : index === 1 ? "⌘" : index === 2 ? "◇" : "✦"}</div><strong>{agent.name.replace(" Agent", "")}</strong><small>{agent.detail.split(" · ")[0]}</small><b>{agent.metric}</b>{index < agents.length - 1 && <span className="flow-line">→</span>}</div>)}
        </div>
        <div className="flow-event"><span className="event-dot" /><div><strong>WO-20260717-0831</strong><p>识别为“暖通空调” · 优先级 P2 · 正在计算最优处理人</p></div><time>刚刚</time></div>
      </div>
      <div className="panel workload-panel"><PanelTitle title="人员负载" subtitle="实时可调度资源" action="全部人员" />
        <div className="worker-summary"><div className="donut"><b>18</b><small>在线</small></div><div className="legend"><span><i className="green" />可调度 <b>7</b></span><span><i className="purple" />作业中 <b>9</b></span><span><i className="gray" />离线 <b>2</b></span></div></div>
        <div className="mini-workers">{workers.slice(0, 3).map((w) => <div key={w.name}><span className="avatar small">{w.name[0]}</span><p><b>{w.name}</b><small>{w.skill} · {w.zone}</small></p><div className="load"><span style={{ width: `${w.load / w.max * 100}%` }} /></div><em>{w.load}/{w.max}</em></div>)}</div>
      </div>
      <div className="panel recent-panel"><PanelTitle title="需要关注" subtitle="按紧急程度和 SLA 排序" action="查看全部" />
        <div className="ticket-list">{tickets.slice(0, 4).map((ticket) => <button key={ticket.id} onClick={() => onOpen(ticket)}><div className={`priority-mark ${ticket.priority}`} /><div className="ticket-main"><span><code>{ticket.id}</code><Pill kind={ticket.priority === "紧急" ? "danger" : ticket.priority === "高" ? "warning" : "neutral"}>{ticket.priority}</Pill></span><strong>{ticket.title}</strong><small>{ticket.area} · {ticket.assignee}</small></div><div className="ticket-sla"><small>SLA 剩余</small><b>{ticket.sla}</b></div><span className="chevron">›</span></button>)}</div>
      </div>
      <div className="panel alert-panel"><PanelTitle title="智能预警" subtitle="巡检 Agent 实时发现" />
        <div className="alert-card warning"><span>!</span><div><strong>北区照明类工单上升</strong><p>近 2 小时同比增加 42%，建议安排专项巡检。</p></div></div>
        <div className="alert-card info"><span>i</span><div><strong>陈立负载即将饱和</strong><p>当前 3/5，另有 2 个待派任务技能匹配。</p></div></div>
        <button className="outline-wide">生成优化方案 <span>→</span></button>
      </div>
    </section>
  </div>;
}

function Metric({ title, value, change, note, tone, chart }: { title: string; value: string; change: string; note: string; tone: string; chart: number[] }) {
  return <article className={`metric-card ${tone}`}><div className="metric-top"><span>{title}</span><i>↗</i></div><strong>{value}</strong><div className="metric-foot"><span className="up">↑ {change}</span><small>{note}</small></div><div className="sparkline">{chart.map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}</div></article>;
}

function PanelTitle({ title, subtitle, action }: { title: string; subtitle: string; action?: string }) {
  return <div className="panel-title"><div><h2>{title}</h2><p>{subtitle}</p></div>{action && <button>{action} <span>→</span></button>}</div>;
}

function TicketPool({ filtered, selected, setSelected, query, setQuery, statusFilter, setStatusFilter, onDispatch }: { filtered: Ticket[]; selected: Ticket; setSelected: (t: Ticket) => void; query: string; setQuery: (v: string) => void; statusFilter: string; setStatusFilter: (v: string) => void; onDispatch: () => void }) {
  return <div className="page"><div className="section-heading"><div><Pill kind="live">工单全生命周期</Pill><h1>工单池</h1><p>统一管理多模态诉求、AI 识别结果和处置进度。</p></div><div className="view-toggle"><button className="active">列表</button><button>看板</button></div></div>
    <div className="ticket-workspace">
      <section className="panel tickets-table-panel"><div className="table-toolbar"><label className="search wide"><span>⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索工单编号或内容" /></label><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="状态筛选"><option>全部状态</option><option>待识别</option><option>待派单</option><option>处理中</option><option>待回访</option><option>已完成</option></select><button className="filter-btn">筛选 ⌄</button></div>
        <div className="table-head"><span>工单信息</span><span>分类 / 区域</span><span>优先级</span><span>状态</span><span>处理人</span></div>
        <div className="table-body">{filtered.map((ticket) => <button className={selected.id === ticket.id ? "selected" : ""} onClick={() => setSelected(ticket)} key={ticket.id}><span><code>{ticket.id}</code><strong>{ticket.title}</strong><small>{ticket.media.join(" · ")} · {ticket.created}</small></span><span><b>{ticket.category}</b><small>{ticket.area}</small></span><span><Pill kind={ticket.priority === "紧急" ? "danger" : ticket.priority === "高" ? "warning" : ticket.priority === "中" ? "info" : "neutral"}>{ticket.priority}</Pill></span><span><Pill kind={ticket.status === "处理中" ? "active" : ticket.status === "已完成" ? "success" : "neutral"}>{ticket.status}</Pill></span><span><span className="avatar xsmall">{ticket.assignee === "待分配" ? "?" : ticket.assignee[0]}</span>{ticket.assignee}</span></button>)}</div>
      </section>
      <aside className="panel detail-panel"><div className="detail-head"><div><code>{selected.id}</code><h2>{selected.title}</h2></div><button aria-label="更多操作">•••</button></div>
        <div className="detail-pills"><Pill kind={selected.priority === "紧急" ? "danger" : "warning"}>{selected.priority}优先级</Pill><Pill kind="active">{selected.status}</Pill></div>
        <div className="ai-summary"><div className="ai-title"><span>✦</span><strong>AI 多模态摘要</strong><em>{selected.confidence || "分析中"}{selected.confidence ? "%" : ""}</em></div><p>用户反馈“{selected.title}”，位置位于{selected.area}。系统已结合文字与附件完成关键信息抽取，建议由具备 <b>{selected.category}</b> 技能的人员优先处置。</p><div className="tags"><span>{selected.category}</span><span>{selected.area}</span><span>需现场处理</span></div></div>
        <dl className="meta-grid"><div><dt>提交人</dt><dd>{selected.reporter}</dd></div><div><dt>创建时间</dt><dd>今日 {selected.created}</dd></div><div><dt>当前处理人</dt><dd>{selected.assignee}</dd></div><div><dt>SLA 剩余</dt><dd className="danger-text">{selected.sla}</dd></div></dl>
        <h3>Agent 决策链</h3><ol className="decision-chain"><li className="done"><span>✓</span><div><b>多模态融合</b><small>文字、图像特征已标准化</small></div><time>32 ms</time></li><li className="done"><span>✓</span><div><b>意图识别</b><small>{selected.category} · 置信度 {selected.confidence}%</small></div><time>41 ms</time></li><li className={selected.assignee === "待分配" ? "running" : "done"}><span>{selected.assignee === "待分配" ? "⌁" : "✓"}</span><div><b>智能调度</b><small>{selected.assignee === "待分配" ? "正在评估 7 名可调度人员" : `已选择 ${selected.assignee}`}</small></div><time>{selected.assignee === "待分配" ? "进行中" : "42 ms"}</time></li></ol>
        {selected.assignee === "待分配" && <button className="primary full" onClick={onDispatch}>✦ 执行智能派单</button>}
      </aside>
    </div>
  </div>;
}

function AgentCenter() { return <div className="page"><div className="section-heading"><div><Pill kind="live"><span className="pulse" /> 5 / 5 在线</Pill><h1>多智能体协同引擎</h1><p>轻量状态机驱动，所有决策可解释、可回放、可人工接管。</p></div><button className="primary">＋ 注册 Agent</button></div><div className="agent-cards">{[...agents, { name: "预警巡检 Agent", detail: "积压 · 负载 · 热点", state: "巡检中", metric: "3 条", tone: "rose" }].map((agent, i) => <article className={`agent-card ${agent.tone}`} key={agent.name}><div className="agent-card-head"><span>{i + 1}</span><Pill kind="success">{agent.state}</Pill></div><h2>{agent.name}</h2><p>{agent.detail}</p><div className="agent-stats"><div><small>本日处理</small><b>{[284, 261, 398, 176, 48][i]}</b></div><div><small>成功率</small><b>{["96.4%", "99.8%", "99.9%", "100%", "98.2%"][i]}</b></div><div><small>平均耗时</small><b>{["41ms", "42ms", "18ms", "27ms", "1.2s"][i]}</b></div></div><button>查看运行详情 <span>→</span></button></article>)}</div><section className="panel state-panel"><PanelTitle title="全局状态中心" subtitle="Agent 间共享状态与资源冲突仲裁" action="打开观测台" /><div className="state-stream">{["intent.completed", "dispatch.worker.locked", "flow.sla.warning", "credit.settlement.done"].map((event, i) => <div key={event}><span className={`event-code c${i}`}>{event}</span><p>{["工单 WO-0831 已完成意图识别", "锁定人员资源：李昂 / TTL 30s", "3 张工单将在 30 分钟内超时", "完成 18 条积分结算记录"][i]}</p><time>{["2s", "4s", "18s", "1m"][i]} ago</time></div>)}</div></section></div>; }

function Workforce() { return <div className="page"><div className="section-heading"><div><Pill kind="live">18 人在线</Pill><h1>人员调度</h1><p>按技能、区域和实时负载统一管理现场处理资源。</p></div><button className="primary">排班管理</button></div><div className="workforce-grid">{workers.map((w) => <article className="worker-card panel" key={w.name}><div className="worker-head"><span className="avatar large">{w.name[0]}</span><div><h2>{w.name}</h2><p>{w.skill} · {w.zone}</p></div><Pill kind={w.state === "可调度" ? "success" : "active"}>{w.state}</Pill></div><div className="score-row"><span>综合评分 <b>{w.score}</b></span><span>当前负载 <b>{w.load}/{w.max}</b></span></div><div className="capacity"><span style={{ width: `${w.load / w.max * 100}%` }} /></div><dl><div><dt>今日完成</dt><dd>{w.score % 7 + 8}</dd></div><div><dt>平均响应</dt><dd>{w.score % 5 + 3} 分钟</dd></div><div><dt>按时率</dt><dd>{w.score}%</dd></div></dl><button>查看人员详情</button></article>)}</div></div>; }

function Analytics() { const bars = [62, 81, 73, 90, 68, 86, 96]; return <div className="page"><div className="section-heading"><div><Pill kind="live">数据截至 10:00</Pill><h1>数据分析</h1><p>洞察工单趋势、服务效率与高频问题分布。</p></div><button className="outline-btn">导出报告</button></div><div className="analytics-top"><section className="panel trend-card"><PanelTitle title="近 7 日工单趋势" subtitle="受理量与完成量" action="最近 7 天" /><div className="big-chart"><div className="y-axis"><span>400</span><span>300</span><span>200</span><span>100</span><span>0</span></div><div className="bars">{bars.map((b, i) => <div key={i}><span className="bar accepted" style={{ height: `${b}%` }} /><span className="bar completed" style={{ height: `${b * .82}%` }} /><small>{["周六", "周日", "周一", "周二", "周三", "周四", "今天"][i]}</small></div>)}</div></div><div className="chart-legend"><span><i className="accepted" />受理量</span><span><i className="completed" />完成量</span></div></section><section className="panel category-card"><PanelTitle title="工单分类占比" subtitle="本月累计 6,842 单" /><div className="category-visual"><div className="category-donut"><b>6,842</b><small>工单总量</small></div><div className="category-list">{[["设备故障", 32, "cyan"], ["安全隐患", 24, "violet"], ["环境卫生", 18, "lime"], ["综合服务", 15, "amber"], ["其他", 11, "gray"]].map((c) => <div key={String(c[0])}><span><i className={String(c[2])} />{c[0]}</span><b>{c[1]}%</b></div>)}</div></div></section></div><div className="analytics-metrics"><Metric title="平均响应时长" value="4.8 min" change="18.4%" note="优于上周" tone="cyan" chart={bars} /><Metric title="一次解决率" value="91.6%" change="3.2%" note="持续提升" tone="lime" chart={bars.slice().reverse()} /><Metric title="用户满意度" value="4.86" change="0.12" note="满分 5.0" tone="violet" chart={bars} /></div></div>; }

function CreateModal({ onClose, onSubmit }: { onClose: () => void; onSubmit: (form: FormData) => void }) { return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><form className="modal" action={onSubmit}><div className="modal-head"><div><Pill kind="live">多模态接入</Pill><h2>新建工单</h2><p>提交后将由 Agent 自动识别、分类并派单。</p></div><button type="button" onClick={onClose} aria-label="关闭">×</button></div><label>问题描述<textarea name="title" placeholder="请描述发生了什么、具体位置和影响范围…" required /></label><div className="form-row"><label>预选分类<select name="category"><option>由 AI 自动识别</option><option>设备故障</option><option>安全隐患</option><option>环境卫生</option><option>综合服务</option></select></label><label>紧急程度<select name="priority"><option>中</option><option>高</option><option>紧急</option><option>低</option></select></label></div><label>发生区域<select name="area"><option>中心区</option><option>东区 · A3</option><option>西区 · B2</option><option>北区 · 1 号门</option><option>南区 · C1</option></select></label><div className="upload-zone"><span>＋</span><div><b>添加图片、语音或短视频</b><small>支持 JPG、PNG、MP3、MP4，单文件不超过 50 MB</small></div><button type="button">选择文件</button></div><div className="modal-actions"><button type="button" onClick={onClose}>取消</button><button className="primary" type="submit">提交并启动 AI 分析</button></div></form></div>; }
