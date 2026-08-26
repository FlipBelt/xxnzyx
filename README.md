# FLIPBELT 线下“40秒能装挑战”

本仓库包含活动用户端、工作人员后台和 FastAPI 后端。

详细需求与实施方案见 [项目需求开发文档与实施方案.md](./项目需求开发文档与实施方案.md)。

## 目录

- `apps/participant`：Taro + Vue 3 用户端，发布到微信小程序和 H5。
- `apps/admin`：Vue 3 + Vite 工作人员后台。
- `backend`：FastAPI + PostgreSQL 后端。
- `deploy`：Docker Compose 与 Nginx 部署配置。
- `assets`：后续统一管理的活动素材；当前原始测试素材保留在仓库根目录。

## 开发原则

- 所有业务规则以“活动配置”驱动，不写死在页面中。
- 分数、排名、奖励和抽奖资格均由后端计算。
- 真实密钥只放在环境变量中，不提交到仓库。

## 本地启动

首次安装前端依赖：

```powershell
pnpm install
```

启动 API（本地开发可用 SQLite；正式环境只使用 PostgreSQL）：

```powershell
Set-Location backend
$env:DATABASE_URL = 'sqlite+aiosqlite:///./local-dev.db'
$env:APP_ENV = 'development'
uv run uvicorn app.main:app --host 127.0.0.1 --port 8100
```

另开两个终端分别启动用户端与后台：

```powershell
pnpm --filter @flipbelt/participant dev:h5
pnpm --filter @flipbelt/admin dev
```

- 用户 H5：构建后由 Taro 输出；开发时以终端显示的地址为准。
- 后台：`http://127.0.0.1:5188`。本地开发数据库首次初始化时可使用 `admin / admin123`；部署环境请以服务器管理员配置为准，登录页不会自动填入测试账号。
- API 文档：`http://127.0.0.1:8100/docs`。

## 构建与检查

```powershell
pnpm --filter @flipbelt/participant build:h5
pnpm --filter @flipbelt/participant build:weapp
pnpm --filter @flipbelt/admin build
Set-Location backend; uv run ruff check .; uv run pytest -q
```

## 微信上线前必须补齐

当前代码已经可以构建微信小程序包，H5 本地测试也以手机号做唯一身份。正式微信入口必须由后端使用小程序 AppID、AppSecret 通过 `wx.login` 的 code 换取 OpenID；这些平台凭据、备案主体、已备案域名与合法请求域名只能在微信主体准备完成后配置，不能用本地测试身份替代。

## 当前测试服务器

已部署在公司 ECS 的同一 HTTP 入口下，避免占用额外公网端口：

- 参赛端：`http://121.41.164.222/flipbelt/`
- 管理后台：`http://121.41.164.222/flipbelt-admin/`
- API：`http://121.41.164.222/flipbelt-api/api/v1/health`

服务器使用 PostgreSQL、独立 systemd 服务 `flipbelt-challenge`（仅监听 `127.0.0.1:18100`）和现有 Nginx 反向代理。待公司域名与 HTTPS 证书准备好后，应将以上 IP 地址替换为正式 HTTPS 域名，并重新构建用户端与后台。
