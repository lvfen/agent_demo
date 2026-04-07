# Customer Service Demo

一个单会话的客服演示项目，包含：

- `frontend/`：React + Vite 的客户侧聊天页和客服工作台
- `backend/`：FastAPI + WebSocket 服务
- AI 优先接待、人工接管、再交还 AI 的完整链路
- 基于 LiteLLM / DeepAgent 的回复生成路径

## 项目结构

- `frontend/src/pages/CustomerChatPage.tsx`：客户侧页面
- `frontend/src/pages/AgentWorkbenchPage.tsx`：客服工作台
- `backend/app/main.py`：HTTP / WebSocket 入口
- `backend/app/ws_manager.py`：会话事件流、接管逻辑、AI 回复流式分发
- `backend/app/prompting.py`：客服 system prompt
- `backend/app/agent_service.py`：模型调用和受限请求判定

## 环境要求

- Python 3.12+
- Node.js + npm
- 一个可用的 LiteLLM 兼容模型入口

## 环境变量

先复制一份环境变量文件：

```bash
cp .env.example .env
```

默认示例：

```env
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=your-litellm-key
LITELLM_MODEL=gpt-4o-mini
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

说明：

- 后端会按顺序读取仓库根目录的 `.env` 和 `backend/.env`
- 前端默认访问 `http://localhost:8000` 和 `ws://localhost:8000`
- 如果你的 LiteLLM 路由本质上代理的是 Gemini，也可以改用 `GEMINI_BASE_URL`、`GEMINI_API_KEY`、`GEMINI_MODEL`

## 如何启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

启动后可检查：

```bash
curl http://localhost:8000/api/health
```

预期返回：

```json
{"status":"ok"}
```

## 如何启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

默认访问地址：

- 客户页：`http://localhost:5173/customer`
- 客服工作台：`http://localhost:5173/agent`

根路径 `/` 会自动跳转到 `/customer`。

## 如何复现 Demo

建议同时打开两个窗口：

- 一个打开客户页 `http://localhost:5173/customer`
- 一个打开客服工作台 `http://localhost:5173/agent`

### 1. 复现 AI 自动接待

1. 确认后端和前端都已启动。
2. 在客户页发送一条普通消息，例如“我想咨询一下订单进度”。
3. 预期结果：
   - 客户页会显示“正在为你核实...”
   - 工作台会同步看到客户消息
   - AI 会自动流式回复

### 2. 复现人工接管

1. 在工作台点击 `Take Over`。
2. 此时会话归属会变成 `human_active`。
3. 在工作台输入一条人工回复并发送。
4. 预期结果：
   - 客户页能收到这条人工回复
   - 之后客户再发消息时，后端不会自动触发 AI 回复

### 3. 复现交还 AI

1. 在工作台点击 `Release to AI` 或 `Resume AI`。
2. 再回到客户页发送新消息。
3. 预期结果：
   - 会话重新进入 AI 处理
   - 新消息会再次触发 AI 自动回复

### 4. 复现“待跟进”分支

当前代码里，受限请求是靠 `backend/app/agent_service.py` 里的关键词判断触发的。为了稳定复现，请直接发送包含以下英文关键词的内容：

- `refund`
- `bank card`
- `compensation`
- `payout`
- `account info`

例如：

- `I want a refund`
- `I need to change my bank card`

预期结果：

- 客户页会收到一条安全兜底回复：`这件事我先帮你核实一下，请稍等。`
- 工作台内部状态会变成待跟进
- 工作台会收到仅内部可见的 `FOLLOWUP_REQUIRED` 提示
- 这一步不会再触发 AI 自动生成正式答复

## 如何调整 Prompt

### 1. 修改客服 system prompt

主 prompt 在 [backend/app/prompting.py](/Users/longquan/development/docs/agent-demo/backend/app/prompting.py) 里的 `SUPPORT_SYSTEM_PROMPT`：

```python
SUPPORT_SYSTEM_PROMPT = """
你是一名在线客服。
不要说自己是 AI、模型、助手或机器人。
...
""".strip()
```

如果你想调整客服语气、禁忌表达、是否先安抚再处理，直接改这里。

### 2. 理解 prompt 是怎么拼出来的

同一个文件里的 `build_support_instructions()` 会把下面三部分拼接成最终 system instructions：

- `SUPPORT_SYSTEM_PROMPT`
- 会话摘要 `summary`
- 当前内部状态 `agent_status`

这意味着你不仅能改固定提示词，也能把“摘要怎么写”“状态怎么影响回复”做成更强的控制信号。

### 3. 调整模型和推理入口

模型配置来自 `.env`：

- `LITELLM_BASE_URL`
- `LITELLM_API_KEY`
- `LITELLM_MODEL`

实际调用在 [backend/app/agent_service.py](/Users/longquan/development/docs/agent-demo/backend/app/agent_service.py) 里完成，目前使用 `ChatOpenAI(..., temperature=0.4, timeout=20, max_retries=1)`。

如果你想调整：

- 模型型号：改 `.env` 里的 `LITELLM_MODEL`
- 模型网关地址：改 `.env` 里的 `LITELLM_BASE_URL`
- 输出发散度：改 `temperature`
- 超时和重试：改 `timeout`、`max_retries`

### 4. 调整“什么情况下不要直接答”

“受限请求”的判定不在 prompt 里，而在 [backend/app/agent_service.py](/Users/longquan/development/docs/agent-demo/backend/app/agent_service.py) 的 `evaluate_request()` 里。

如果你要改变 demo 行为，例如：

- 哪些问题必须转内部跟进
- 返回什么 holding message
- 跟进后把 `agent_status` 改成什么

应该改这个函数，而不是只改 prompt。

## 验证命令

后端测试：

```bash
cd backend
pytest -v
```

前端测试和构建：

```bash
cd frontend
npm test -- --run
npm run build
```
