# `ingest-normalize` adapter 与归一化规则

## 1. 文档目的

本文档定义 `ingest-normalize` 当前阶段最小可落地的两类技术细节：

- 来源 adapter 的统一接口和运行约束
- `normalize_candidates` 所依赖的基础归一化规则

本文档的目标不是一次写满所有来源，而是给第一版 skill 一个稳定、可扩展、但不过度抽象的技术边界。

## 2. adapter 设计目标

### 2.1 adapter 负责的事

- 访问来源
- 处理认证
- 处理分页或游标
- 将来源原始返回转成统一 `RawFeedItem`

### 2.2 adapter 不负责的事

- 对象持久化
- 失败 ledger 写入
- URL 去重
- 摘要生成
- 内容价值判断

## 3. 最小 adapter 接口

每种来源类型都应实现同一组最小接口。

### 3.1 `validate_source_config`

输入：

- 单来源配置

输出：

- 规范化后的来源配置
- 或配置级失败

职责：

- 校验必要字段
- 校验 auth 引用是否可解析
- 校验来源类型和抓取策略是否匹配

### 3.2 `build_fetch_request`

输入：

- `SourceDescriptor`
- `SourceSyncPlan`

输出：

- 本轮抓取请求上下文

职责：

- 组装 URL、headers、query、cursor
- 注入超时、分页、限流参数

### 3.3 `fetch_batch`

输入：

- 抓取请求上下文

输出：

- 原始来源响应
- 或抓取级失败

职责：

- 发起网络请求
- 处理认证失败
- 处理超时和重试
- 收集分页结果

### 3.4 `convert_response_to_feed_items`

输入：

- 原始来源响应

输出：

- `RawFeedItem[]`
- `next_cursor`

职责：

- 把来源返回统一成 feed 结构
- 保留原始 payload
- 不做语义清洗

## 4. 支持的第一批来源类型

第一版只建议覆盖以下来源：

| adapter_type | 说明 |
|---|---|
| `RSS` | 标准 RSS/Atom |
| `RSSHUB` | 通过 RSSHub 暴露的 feed |
| `GITHUB_FEED` | GitHub Feed 或 GitHub 事件流 |
| `CUSTOM_HTTP` | 自定义 HTTP 拉取器，返回可映射列表 |

当前阶段不建议提前支持：

- 需要浏览器驱动的复杂抓取
- 登录态高度耦合的站点
- JavaScript 渲染后才能读取的页面

## 5. 认证、超时与重试

### 5.1 认证规则

- 配置文件只保存 `auth_ref`
- 真正密钥从环境变量、凭证文件或外部 secret store 解析
- 认证失败统一记为 `AUTH_ERROR`

### 5.2 超时规则

建议最小超时策略：

- 单请求超时：10 秒到 30 秒
- 单来源总超时：60 秒到 120 秒

超过单请求超时：

- 记为 `NETWORK_ERROR`
- 允许有限重试

### 5.3 重试规则

当前阶段建议：

- 只对网络错误和临时 5xx 重试
- 默认最多重试 2 次
- 使用简单指数退避

不重试：

- 配置错误
- 认证失败
- 明确的 4xx 参数错误

## 6. 分页与游标规则

### 6.1 分页统一语义

即使底层来源没有显式分页，也统一暴露：

- `cursor`
- `next_cursor`

这样可以让 `SourceSyncPlan` 和 `FetchedSourceBatch` 保持稳定。

### 6.2 游标来源

游标可以来自：

- 时间窗边界
- 来源返回的下一页 token
- 最后一条条目的时间戳或 ID

### 6.3 当前阶段不做的复杂游标逻辑

- 不做跨来源统一排序游标
- 不做多游标合并
- 不做自动游标修复

## 7. 条目映射最小规则

`RawFeedItem` 到 `SourceEntryDraft` 的映射至少满足：

| 字段 | 规则 |
|---|---|
| `source_id` | 继承来源配置 |
| `source_name` | 继承来源配置 |
| `origin_item_id` | 优先用来源原生 ID；无则退化到稳定 URL 或来源内组合键 |
| `title` | 原样保留，不在此阶段洗稿 |
| `url` | 原样保留，归一化放到后一步 |
| `summary` | 原样保留 |
| `author` | 缺失允许为空 |
| `published_at` | 保留原始时间，解析失败允许为空 |
| `fetched_at` | 由运行时补入 |
| `raw_payload` | 保留原始结构 |

## 8. 基础归一化规则

### 8.1 URL 归一化

`canonical_url` 的目标是“稳定引用”，不是“内容去重”。

当前阶段建议只做：

- 去掉首尾空白
- 统一协议和 host 大小写
- 去掉默认端口
- 去掉 fragment
- 对已知追踪参数做有限清理，如 `utm_*`

当前阶段明确不做：

- 基于正文内容改写 URL
- 跨站点规范 URL 合并
- 把不同文章误判为同一 canonical URL

### 8.2 URL 指纹

`url_fingerprint` 从 `canonical_url` 派生。

要求：

- 同一 `canonical_url` 在同一实现版本下必须稳定
- 哈希算法可以后续定，但结果必须可重现

### 8.3 标题归一化

`normalized_title` 当前阶段建议只做：

- 去掉首尾空白
- 压缩连续空白字符
- 统一常见全角/半角空格

当前阶段不做：

- 语义改写
- 翻译
- 去情绪化
- 标题相似度判断

### 8.4 语言补全

`language` 的优先级：

1. 来源显式提供的语言字段
2. 来源级默认语言
3. 基于标题/摘要的轻量检测
4. 仍无法确定则留空

当前阶段不要求：

- 高精度多语种检测
- 正文级语言识别

### 8.5 发布时间规则

`published_at` 处理规则：

- 能解析为 ISO 8601 就统一写 ISO 8601
- 仅有日期无时间时，保留日期语义
- 来源未提供时允许为空

当前阶段不做：

- 推断真实发布时间
- 与抓取时间做内容新旧判断

## 9. 幂等规则

### 9.1 来源条目幂等

同一来源内，优先依赖：

- `origin_item_id`

若来源没有稳定 ID，再退化到：

- `canonical_url`
- 或来源内组合键

### 9.2 快照幂等

`SourceEntry` 是快照对象，因此允许同一逻辑条目在不同抓取时间形成不同快照。

不变的是：

- `source_entry_id` 对应逻辑身份

变化的是：

- `source_entry_snapshot_id`

## 10. 最小错误分类映射

建议 adapter 层使用如下错误映射：

| 场景 | failure_type |
|---|---|
| 配置缺字段、类型错误 | `CONFIG_ERROR` |
| 凭证缺失、401、403 | `AUTH_ERROR` |
| 连接失败、超时、DNS 问题 | `NETWORK_ERROR` |
| 返回格式无法解析 | `PARSE_ERROR` |
| 字段映射失败 | `MAPPING_ERROR` |
| 写文件或写库失败 | `PERSIST_ERROR` |
| 归一化规则异常 | `NORMALIZE_ERROR` |

## 11. 当前阶段明确不做

第一版 `ingest-normalize` 不提前做以下能力：

- 浏览器自动化抓取
- 正文抽取
- 智能内容清洗
- 基于正文的 canonical 合并
- 跨来源实体对齐
- 自适应限流
- 自动修复失效来源

## 12. 落地建议

第一版实现建议保持“单 workflow、单 adapter 注册表、单归一化规则模块”：

- `adapters/registry.py`
- `adapters/rss.py`
- `adapters/rsshub.py`
- `adapters/github_feed.py`
- `adapters/custom_http.py`
- `normalizers/url.py`
- `normalizers/title.py`
- `normalizers/language.py`

不要在第一版提前做插件系统；先把接口稳定，再决定是否抽成更通用的扩展机制。
