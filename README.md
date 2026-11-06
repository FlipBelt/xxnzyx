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

## 入口与发布配置

- 现场参赛入口：`https://nzyx.flipbeltchina.com/`。
- 微信入口使用 `/wx-entry-20261106`；根地址和旧微信二维码路径跳转到新入口，避免继续使用旧WebView快照。
- 正式域名后台目标：`https://nzyx.flipbeltchina.com/flipbelt-admin/`；由 `deploy/nzyx.flipbeltchina.com.conf` 中的专用路径提供，不回落到参赛端。
- 以下IP入口为兼容入口，避免占用额外公网端口：


- 参赛端：`http://121.41.164.222/flipbelt/`
- 管理后台：`http://121.41.164.222/flipbelt-admin/`
- API：`http://121.41.164.222/flipbelt-api/api/v1/health`

服务器使用 PostgreSQL、独立 systemd 服务 `flipbelt-challenge`（仅监听 `127.0.0.1:18100`）和 Nginx。域名版H5构建前设置 `TARO_PUBLIC_PATH=/`；兼容IP版使用 `TARO_PUBLIC_PATH=/flipbelt/`。后台保持 `VITE_BASE=/flipbelt-admin/`。

## 登录与报名恢复

后台接口始终验证登录，旧的 `ADMIN_AUTH_ENABLED=false` 不再提供旁路。正式环境拒绝文档中的开发默认密码。管理员可维护规则、补录、删除成绩及抽奖；录分人员可查询、录入及修正成绩。

同一活动、手机号、姓名和号码牌完全匹配的重复报名返回原报名编号，不重复建档；工作人员补录的记录沿用同一恢复路径。不一致的资料需工作人员核对。恢复不再仅凭手机号签发身份，但完整资料匹配仍不等同于手机号持有验证。

正式运行配置固定 `APP_ENV=production`，必须通过环境变量提供独立的 `JWT_SECRET`，至少32字符，禁止使用示例占位值。既有管理员账号与独立密钥必须在发布前确认；不把开发默认账号带入现场。

## 品牌与移动端

采用 [公司设计系统0.2.0](https://github.com/J21NIANYI/company-design-system) 的Experimental契约与候选语义映射：白/浅灰底、墨黑文字、荧黄绿主操作。共享样式与登记的墨黑Logo位于 `apps/shared/branding/`；Logo对应数字中心固定提交 `1a8d91a353f066e854b16dde4f243eba222faa90` 的 `frontend/public/logo.svg`，保持原比例和颜色。

H5使用正常文档滚动，不锁定键盘打开前的页面高度。输入字号至少16 CSS像素，主操作可通过滚动和键盘到达；页面保持浏览器缩放能力。Chromium/WebKit模拟不代替iPhone微信真机验收。

## 回归验证

后端测试必须显式使用独立本地数据库，禁止指向现场库：

```powershell
$env:APP_ENV = 'test'
$env:DATABASE_URL = 'sqlite+aiosqlite:///./local-tests.db'
uv run --directory backend ruff check app tests ../tests/verify_nginx.py
uv run --directory backend pytest -q
```

并发重试测试仅在PostgreSQL运行；SQLite下会跳过。使用独立PostgreSQL测试库时，以环境变量替换上述连接，五个并发报名请求应得到同一报名编号。

`tests/ui-smoke.mjs` 针对构建产物启动仅监听本机的测试服务，使用合成API响应，覆盖两种浏览器、三种窄屏、聚焦及视口恢复、断网重试、回执丢失、后台登录过期和Logo加载。需要本地Playwright与Chromium/Chrome、WebKit；可通过 `PLAYWRIGHT_MODULE` 指定已安装模块的文件URL，无需修改业务依赖。

```powershell
node tests/ui-smoke.mjs
python tests/verify_nginx.py
```

Nginx验证需要Docker与 `nginx:alpine`，只替换本地测试副本的TLS监听/证书行，沿用实际路径规则；不检查现场证书或执行发布。
