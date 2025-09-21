# Vertexflow Memory 模块设计文档（Redis/MySQL 综合设计）

## 1. 模块定位

**Memory** 是 Vertexflow 的会话记忆层，用于统一管理用户会话数据，提供跨节点、跨轮次的状态存取能力。它是**纯存储层**，不包含业务决策、路由逻辑、任务调度等功能。

目标：

- 统一管理去重、历史、上下文、临时数据、用户画像、长期知识
- 屏蔽底层存储实现（Redis、MySQL、文件等）
- 支持高性能、低延迟、多租户

---

## 2. 功能需求

### 2.1 核心功能

1. **去重（Deduplication）**

   - 基于 `user_id + unique_key`（msg\_id 或 timestamp hash）
   - TTL 可配置（默认 1 小时）
   - 支持语义去重（选配，embedding 相似度过滤）

2. **历史记录（Episodic Memory）**

   - 保存用户与系统的消息记录（文本/图片/事件等）
   - 按时间顺序存储（最新在前）
   - 支持有界队列（如保留最近 200 条）
   - 异步片段化摘要（减少存储与检索成本）

3. **上下文（Context）**

   - 存储会话范围的键值对（KV）
   - 数据无业务语义，仅作状态缓存
   - 可设置 TTL（如 30 分钟会话过期）

4. **临时数据（Ephemeral Data）**

   - 存储短期有效的任务结果或中间状态
   - TTL 默认 30 分钟，可配置

5. **用户画像（Profile Memory）**

   - 结构化 KV（如 `name`, `lang`, `timezone`）
   - 支持变更轨迹与可信度评分

6. **长期知识（Knowledge Memory）**

   - 使用 embedding 存储持久知识粒度（Facts/Notes/Docs）
   - 支持关键字 + 向量混合检索

7. **速率控制（Rate Limiting）**

   - 按用户+时间桶计数，限制请求速率

8. **质量与遗忘（Scoring & Decay）**

   - 每条记忆带评分（freshness/use/feedback）
   - 定期衰减与压缩，保持质量与成本平衡

---

## 3. 非功能性要求

- **传输无关**：支持微信、HTTP API、WebSocket、CLI 等多种来源
- **可替换存储**：默认 Redis，可扩展 MySQL/向量库/全文检索/冷存储
- **高性能**：Redis 作为热数据存储，单次读写延迟 < 5ms
- **持久化保障**：MySQL 作为冷数据与归档存储，提供数据审计和长期保存能力
- **可观测性**：支持监控与指标输出
- **合规性**：支持用户数据导出与擦除

---

## 4. 存储设计

### 4.1 Redis（热数据）

- 去重：`vf:{tenant}:u:{uid}:dedup:{msgid}` → "1" (EX=1h)
- 历史：`vf:{tenant}:u:{uid}:hist` → LIST(JSON)
- 上下文：`vf:{tenant}:u:{uid}:ctx:{key}` → STRING(JSON)
- 临时：`vf:{tenant}:u:{uid}:eph:{key}` → STRING(JSON)
- 画像：`vf:{tenant}:u:{uid}:profile:{key}` → STRING(JSON)
- 计数：`vf:{tenant}:u:{uid}:rate:{bucket}` → INCR(EX)

### 4.2 MySQL（冷数据/长期存储）

- **history** 表：存储全部对话流水，便于检索与分析
- **profile** 表：结构化存储用户画像，支持变更日志
- **knowledge** 表：长期知识库（可选 embedding 存储）
- 定期从 Redis 将过期/淘汰数据落盘归档

---

## 5. 接口设计

```python
class Memory(Protocol):
    def seen(user_id: str, key: str, ttl_sec: int = 3600) -> bool: ...
    def append_history(user_id: str, role: str, mtype: str, content: Dict[str, Any], maxlen: int = 200) -> None: ...
    def recent_history(user_id: str, n: int = 20) -> List[Dict[str, Any]]: ...
    def ctx_set(user_id: str, key: str, value: Any, ttl_sec: Optional[int] = None) -> None: ...
    def ctx_get(user_id: str, key: str) -> Optional[Any]: ...
    def ctx_del(user_id: str, key: str) -> None: ...
    def set_ephemeral(user_id: str, key: str, value: Any, ttl_sec: int = 1800) -> None: ...
    def get_ephemeral(user_id: str, key: str) -> Optional[Any]: ...
    def del_ephemeral(user_id: str, key: str) -> None: ...
    def incr_rate(user_id: str, bucket: str, ttl_sec: int = 60) -> int: ...
```

---

## 6. Redis + MySQL 数据流

1. **写路径**
   - 实时写入 Redis（热数据）
   - 异步批量同步到 MySQL（冷数据）
2. **读路径**
   - 优先读 Redis 热数据
   - 热数据缺失时从 MySQL 冷数据加载（可选回写 Redis）

---

## 7. MVP 实现重点（Redis 版）

- 去重（seen）
- 历史（append/recent）
- 上下文（ctx\_set/get/del）
- 临时数据（set/get/del）
- 速率控制（incr\_rate）
- 基础单元测试 + 性能基准

> MySQL 部分可在 MVP 之后实现，初期仅需 Redis 保证功能与性能

---

## 11. 存储架构（Redis + MySQL 综合设计）

为兼顾**低延迟**与**长期持久化/统计分析**，建议：

- **Redis：热数据 + 高并发**
  - 去重、速率限制、上下文、临时数据、最近 N 条历史（如 200 条）
- **MySQL：冷/温数据 + 强一致查询**
  - 全量历史归档、用户画像变更轨迹、知识库主存（文本/元数据），用于查询、审计、离线统计
- **可选层**：向量库（Milvus/pgvector）与全文检索（Meilisearch/Elastic）

### 分层职责

- 写入优先 Redis；异步归档至 MySQL（CQRS/事件溯源思想）
- 读取：
  - 近实时/对话上下文 → Redis
  - 全量检索/审计/统计 → MySQL（或 MySQL + 向量/全文）

---

## 12. 数据模型：MySQL 设计（逻辑表）

### 12.1 表：episodic\_history（对话历史）

```sql
CREATE TABLE episodic_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(64) NOT NULL,
  user_id   VARCHAR(128) NOT NULL,
  role ENUM('user','assistant','system') NOT NULL,
  mtype VARCHAR(32) NOT NULL, -- text/image/event
  content JSON NOT NULL,
  channel VARCHAR(32) NULL,   -- wechat/web/cli
  tags JSON NULL,
  freshness_score FLOAT DEFAULT 1.0,
  use_count INT DEFAULT 0,
  feedback_score FLOAT DEFAULT 0,
  created_at DATETIME(3) NOT NULL,
  INDEX idx_user_time(tenant_id, user_id, created_at),
  INDEX idx_user_role(tenant_id, user_id, role)
) ENGINE=InnoDB;
```

### 12.2 表：user\_profile（用户画像）

```sql
CREATE TABLE user_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(64) NOT NULL,
  user_id   VARCHAR(128) NOT NULL,
  pkey VARCHAR(64) NOT NULL,  -- 如 timezone/lang
  pvalue JSON NOT NULL,
  confidence FLOAT DEFAULT 0.8,
  updated_at DATETIME(3) NOT NULL,
  UNIQUE KEY uk_profile (tenant_id, user_id, pkey)
) ENGINE=InnoDB;
```

### 12.3 表：profile\_change\_log（画像变更轨迹）

```sql
CREATE TABLE profile_change_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(64) NOT NULL,
  user_id   VARCHAR(128) NOT NULL,
  pkey VARCHAR(64) NOT NULL,
  old_value JSON NULL,
  new_value JSON NOT NULL,
  reason VARCHAR(128) NULL,
  confidence FLOAT DEFAULT 0.8,
  created_at DATETIME(3) NOT NULL,
  INDEX idx_user_key_time (tenant_id, user_id, pkey, created_at)
) ENGINE=InnoDB;
```

### 12.4 表：knowledge\_doc（长期知识）

```sql
CREATE TABLE knowledge_doc (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(64) NOT NULL,
  owner_user_id VARCHAR(128) NULL, -- 可为空，表示共享
  title VARCHAR(256) NULL,
  text MEDIUMTEXT NOT NULL,
  source_type VARCHAR(32) NULL, -- note|doc|url
  source_id VARCHAR(128) NULL,
  tags JSON NULL,
  freshness_score FLOAT DEFAULT 0.7,
  use_count INT DEFAULT 0,
  feedback_score FLOAT DEFAULT 0,
  created_at DATETIME(3) NOT NULL,
  updated_at DATETIME(3) NOT NULL,
  FULLTEXT KEY ft_text (title, text)
) ENGINE=InnoDB;
```

> 向量数据建议存外部向量库，保留 `doc_id` 双向引用。

### 12.5 表：erase\_audit（擦除审计）

```sql
CREATE TABLE erase_audit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id VARCHAR(64) NOT NULL,
  user_id   VARCHAR(128) NOT NULL,
  action VARCHAR(32) NOT NULL, -- export|erase
  status VARCHAR(32) NOT NULL, -- started|done|failed
  detail JSON NULL,
  created_at DATETIME(3) NOT NULL
) ENGINE=InnoDB;
```

---

## 13. 读写路径与一致性

### 13.1 写路径（首写 Redis，异步持久）

1. 入口：`seen()` 去重 → `append_history()` 写 Redis → 投递 Outbox（队列）
2. Memory-Worker 消费 Outbox：
   - 落库 MySQL（episodic\_history）
   - 触发画像融合（user\_profile + change\_log）
   - 触发知识抽取/合并（knowledge\_doc 与向量库）

> **保证**：即使 MySQL 暂时不可用，Redis 仍提供近实时对话能力；待恢复后补写（at-least-once）。

### 13.2 读路径

- **实时上下文**：来自 Redis：`recent_history()`、`ctx_*`、`eph_*`
- **审计/统计/全量检索**：MySQL（必要时联动向量/全文）

### 13.3 一致性策略

- **最终一致**：Redis ↔ MySQL 通过 Outbox/重试保证
- **去重一致**：去重仅在 Redis 完成；MySQL 侧以 `(tenant_id, user_id, created_at, hash)` 做幂等保护

---

## 14. 归档、压缩与成本控制

- **分层存储**：Redis 保留最近 N 条，老数据定时落 MySQL 并从 Redis 剪裁
- **片段化摘要**：将 K 条历史合成为一条摘要（写回 MySQL，Redis 可只保留摘要）
- **打分与衰减**：周期性降低低价值条目分值，触发归档/冷存
- **清理与擦除**：基于 `tenant_id/app_id/user_id` 的全量删除流程（Redis + MySQL + 向量/全文）

---

## 15. 本地 Memory 介质（InMemory / 本地文件 / 轻量数据库）

为便于**离线开发、单元测试、轻量部署**，提供一个“本地 memory 介质”作为 Redis/MySQL 的互补：

### 15.1 目标与使用场景

- 离线/CI 环境无 Redis 时仍可运行与测试
- 小型工具或单机脚本无需外部依赖
- 可与 Redis 行为保持一致的接口契约，便于替换

### 15.2 形态

1. **InMemoryMemory**（纯内存）

   - 进程内 `dict/list` 实现，进程退出即丢失
   - 支持 TTL（基于惰性清理 + 定时清理线程）
   - 线程安全：用 `threading.RLock` 保护临界区
   - 用途：单元测试、原型验证

2. **FileMemory（JSONL/本地文件）**

   - 目录结构：
     - `./data/{tenant}/{user}/hist.jsonl`（每行一条 JSON）
     - `./data/{tenant}/{user}/ctx.json`（KV）
     - `./data/{tenant}/{user}/eph.json`（KV+过期时间）
     - `./data/{tenant}/{user}/profile.json`（KV）
   - 写入策略：追加写（JSONL）、定期 `fsync`、按大小/日期滚动（如 50MB 或日切）
   - 并发与锁：文件级独占锁（`fcntl`/`msvcrt`）或基于 `portalocker` 封装
   - TTL：写入 `expires_at` 字段，读取惰性清理
   - 优点：可读可查；缺点：并发/性能有限

3. **SQLiteMemory（可选，轻量 DB）**

   - 单文件 SQLite（WAL 模式），表结构与 MySQL 版相近（简化字段）
   - 适合单机与中小数据量，用于替代 FileMemory

### 15.3 接口契约

- 与 `Memory` 保持一致：`seen / append_history / recent_history / ctx_* / ephemeral_* / incr_rate`
- 语义一致：历史为**有界**；TTL 生效；JSON 可序列化；幂等写

### 15.4 关键实现点

- **InMemory**：
  - 结构：`hist` 用 `deque(maxlen=N)`；`ctx/eph` 用 `dict`，值含 `expires_at`
  - 定时清理：后台线程每 1s 扫描过期键；也在读路径惰性清理
- **FileMemory**：
  - 追加写：`hist.jsonl` 每条包含 `{role,type,content,ts}`；读取时倒序迭代取 N 条
  - 滚动与压缩：超过阈值触发切分；可选 gzip 旧文件
  - 锁：单进程优先，跨进程用文件锁；失败重试退避
- **SQLiteMemory**：
  - 表：`hist(user_id, ts, role, type, content_json)`、`kv(user_id, key, value_json, expires_at)`
  - 索引：`(user_id, ts DESC)`；事务保证原子性

### 15.5 测试与一致性

- 共用测试套：针对 `RedisMemory` 的用例在本地介质上复用
- 允许**性能差异**，但**功能与语义**必须一致

---

## 16. MVP 范围（优先 Redis 版本）

**本期只交付 Redis 实现与接口，MySQL 作为下一阶段接入。**

- ✅ Redis：

  - 去重：`seen()`
  - 历史：`append_history()/recent_history()`（LPUSH+LTRIM，有界）
  - 上下文：`ctx_set/get/del`（STRING/Hash，支持 TTL）
  - 临时：`set/get/del_ephemeral`（TTL）
  - 画像：`profile_set/get`（基于 ctx or 独立 key，先用独立 key）
  - 速率：`incr_rate()`
  - 监控：基础 key 计数、命中/长度指标
  - 工具：按 `user_id` 导出/擦除（仅 Redis 范围）

- ⏭ MySQL（下一阶段）：

  - 表结构创建 + Outbox/Worker 持久化
  - 导出/擦除完整链路（含 MySQL 与向量库）
  - 片段化摘要与合并任务（Worker）

- 🧪 测试：

  - 功能：接口契约、幂等、TTL、裁剪
  - 压力：1k QPS 写入、并发 seen 命中率
  - 恢复：Outbox 堆积后的补写与幂等

---

## 16. 运维与监控（建议）

- Redis：
  - 指标：内存、hits/misses、key 数量、过期率、hist 列表长度分布
  - 告警：内存水位（70%/85%）、QPS 异常、过期失败
- MySQL（接入后）：
  - 慢查询、连接池、表体积与索引命中率
- Worker：
  - 重试队列长度、消费延迟、失败比率

---

## 17. 安全与合规

- 分租户前缀与最小权限账户
- 数据加密：敏感字段可做字段级加密或哈希
- 擦除链路：流水日志与审计记录（erase\_audit）

---

## 18. 里程碑与交付

- **M1（本周）**：Redis MVP（接口 + 实现 + 单测 + 文档）
- **M2（+1\~2 周）**：Outbox/Worker，MySQL 表与持久化落地
- **M3（+2\~3 周）**：摘要/合并策略、监控指标、导出/擦除全链路

