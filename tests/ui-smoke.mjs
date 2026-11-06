import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { readFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const playwright = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' }
const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname)
  const admin = pathname.startsWith('/flipbelt-admin/')
  const root = path.join(repo, admin ? 'apps/admin/dist' : 'apps/participant/dist/h5')
  const relative = admin ? pathname.slice('/flipbelt-admin/'.length) : pathname.replace(/^\/flipbelt\//, '/')
  const filename = path.resolve(root, '.' + (relative.startsWith('/') ? relative : '/' + relative))
  if (!filename.startsWith(root + path.sep) && filename !== root) { response.writeHead(403).end(); return }
  try {
    const target = pathname.endsWith('/') ? path.join(filename, 'index.html') : filename
    const content = await readFile(target)
    response.writeHead(200, { 'Content-Type': mime[path.extname(target)] || 'application/octet-stream' }).end(content)
  } catch { response.writeHead(404).end('Not found') }
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const origin = 'http://127.0.0.1:' + server.address().port
const activity = {
  id: 1, slug: 'local-ui-fixture', title: '本地回归活动', status: 'active',
  challenge_duration_seconds: 40, challenge_limit: 1, draw_threshold: 45,
  leaderboard_name_mode: 'plate_masked_name', rules_text: '本地合成测试规则',
  media_assets: [], score_items: [], reward_tiers: []
}
const screenshots = process.env.UI_SCREENSHOTS_DIR
if (screenshots) await mkdir(screenshots, { recursive: true })
let checks = 0
async function capture(page, name) {
  if (process.env.UI_DEBUG_LAYOUT) console.log(name, await page.evaluate(() => ({
    innerHeight, visualHeight: visualViewport?.height, documentHeight: document.documentElement.scrollHeight,
    rootFont: getComputedStyle(document.documentElement).fontSize,
    panel: document.querySelector('.step-panel') && getComputedStyle(document.querySelector('.step-panel')).height
  })))
  if (screenshots) await page.screenshot({ path: path.join(screenshots, name + '.png'), fullPage: true })
}
async function assertNarrow(page) {
  const sizes = await page.evaluate(() => ({
    width: window.innerWidth, scroll: document.documentElement.scrollWidth,
    bodyOverflow: document.body.style.overflow, htmlOverflow: document.documentElement.style.overflow
  }))
  assert.ok(sizes.scroll <= sizes.width + 1, JSON.stringify(sizes))
  assert.notEqual(sizes.bodyOverflow, 'hidden')
  assert.notEqual(sizes.htmlOverflow, 'hidden')
  checks += 1
}
async function fixture(page, { initialFailures = 0, loseFirstReceipt = false } = {}) {
  const state = { activityReads: 0, posts: 0, records: 0, meReads: 0, profileReady: false, expired: false }
  await page.route('**/flipbelt-api/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const endpoint = url.pathname.split('/api/v1')[1]
    const json = (data, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) })
    if (endpoint === '/activity/current') {
      state.activityReads += 1
      return state.activityReads <= initialFailures ? json({ detail: '测试网络暂不可用' }, 503) : json(activity)
    }
    if (endpoint === '/registrations') {
      state.posts += 1
      state.records = 1
      if (loseFirstReceipt && state.posts === 1) return route.abort('failed')
      return json({ registration_id: 7, status: 'registered', access_token: 'synthetic-participant-token', already_registered: state.posts > 1 }, 201)
    }
    if (endpoint === '/me') {
      state.meReads += 1
      return state.profileReady
        ? json({ registered: true, registration_id: 7, name: '本地测试选手', number_plate: 'LOCAL-07', score: 50, draw_qualified: true, reward: { title: '测试等级', prize_name: '测试奖品' } })
        : json({ detail: '测试资料读取失败' }, 503)
    }
    if (endpoint === '/admin/login') {
      const body = route.request().postDataJSON()
      if (body.password !== 'local-ui-password') return json({ detail: '用户名或密码错误' }, 401)
      return json({ access_token: 'synthetic-admin-token', admin: { id: 1, username: 'fixture-admin', display_name: '本地测试管理员', role: 'admin' } })
    }
    if (endpoint.startsWith('/admin/')) {
      if (state.expired) return json({ detail: '登录状态无效' }, 401)
      assert.equal(route.request().headers().authorization, 'Bearer synthetic-admin-token')
      if (endpoint === '/admin/me') return json({ id: 1, username: 'fixture-admin', display_name: '本地测试管理员', role: 'admin' })
      if (endpoint === '/admin/dashboard') return json({ activity, registered_count: 1, scored_count: 0, pending_score_count: 1, draw_qualified_count: 0, highest_score: 0 })
      if (endpoint === '/admin/config') return json(activity)
      if (endpoint === '/admin/leaderboard') return json({ activity: activity.title, entries: [] })
      if (endpoint === '/admin/draw/candidates') return json({ threshold: 45, items: [] })
      if (endpoint === '/admin/registrations') return json({ items: [] })
    }
    return json({ detail: '未定义测试响应' }, 404)
  })
  return state
}
async function runMobile(browser, engine) {
  for (const [width, height] of [[320, 568], [390, 844], [430, 932]]) {
    const context = await browser.newContext({
      viewport: { width, height }, isMobile: true, hasTouch: true,
      userAgent: engine === 'webkit' ? playwright.devices['iPhone 13'].userAgent : playwright.devices['Pixel 7'].userAgent
    })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    const state = await fixture(page, { loseFirstReceipt: true })
    await page.goto(origin)
    await page.locator('.brand-logo img').waitFor()
    await page.waitForFunction(() => document.querySelector('.brand-logo img')?.naturalWidth > 0)
    checks += 1
    await page.getByText('下一步：填写报名', { exact: true }).click()
    await page.getByText('填写参赛信息', { exact: true }).waitFor()
    await assertNarrow(page)
    for (const [placeholder, value] of [['请输入姓名', '本地测试选手'], ['请输入11位手机号', '13900000001'], ['请输入本场参赛号码牌', 'LOCAL-07']]) {
      const input = page.getByPlaceholder(placeholder)
      await input.fill(value)
      await page.setViewportSize({ width, height: 330 })
      await input.scrollIntoViewIfNeeded()
      await assertNarrow(page)
      const box = await input.boundingBox()
      assert.ok(box && box.x >= -1 && box.x + box.width <= width + 1)
      const font = await input.evaluate(element => getComputedStyle(element).fontSize)
      assert.ok(parseFloat(font) >= 16, font)
      await page.setViewportSize({ width, height })
    }
    await capture(page, engine + '-' + width + '-signup')
    await page.getByText('提交报名并继续', { exact: true }).click()
    await page.getByText('网络连接失败，资料已保留，请检查网络后重试', { exact: true }).waitFor()
    assert.equal(await page.getByPlaceholder('请输入姓名').inputValue(), '本地测试选手')
    await page.getByText('提交报名并继续', { exact: true }).click()
    await page.getByText('观看挑战示范', { exact: true }).waitFor()
    assert.equal(state.posts, 2)
    assert.equal(state.records, 1)
    assert.equal(state.meReads, 0)
    await assertNarrow(page)
    if (width === 320) {
      await page.getByText('下一步：查看计分与奖励', { exact: true }).click()
      await page.getByText('计分与奖励', { exact: true }).first().waitFor()
      await assertNarrow(page)
      await page.getByText('下一步：查看挑战规则', { exact: true }).click()
      await page.getByText('挑战规则', { exact: true }).first().waitFor()
      await assertNarrow(page)
      await page.getByText('下一步：进入现场挑战', { exact: true }).click()
      await page.getByText('刷新我的成绩', { exact: true }).click()
      await page.getByText('成绩加载失败，请联系工作人员。', { exact: true }).waitFor()
      state.profileReady = true
      await page.getByText('刷新我的成绩', { exact: true }).click()
      await page.getByText('我的挑战成绩', { exact: true }).waitFor()
      await page.waitForFunction(() => document.querySelector('img.draw-qr')?.naturalWidth > 0)
      await assertNarrow(page)
      checks += 3
    }
    assert.deepEqual(errors, [])
    checks += 5
    await context.close()
  }
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const page = await context.newPage()
  await fixture(page, { initialFailures: 2 })
  await page.goto(origin)
  await page.getByText('活动信息暂时无法加载', { exact: true }).waitFor()
  await page.getByText('重新加载', { exact: true }).click()
  await page.getByText('下一步：填写报名', { exact: true }).waitFor()
  await assertNarrow(page)
  await capture(page, engine + '-home')
  checks += 1
  await context.close()
}
async function runAdmin(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const state = await fixture(page)
  await page.goto(origin + '/flipbelt-admin/')
  await page.getByRole('heading', { name: '登录现场管理台' }).waitFor()
  await page.locator('input').nth(0).fill('fixture-admin')
  await page.locator('input').nth(1).fill('wrong')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.getByText('用户名或密码错误', { exact: true }).waitFor()
  await page.locator('input').nth(1).fill('local-ui-password')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.getByRole('heading', { name: '现场概况', exact: true }).waitFor()
  await page.getByText('活动概览', { exact: true }).waitFor()
  await capture(page, 'admin-dashboard')
  await page.reload()
  await page.getByText('活动概览', { exact: true }).waitFor()
  await page.setViewportSize({ width: 375, height: 667 })
  await assertNarrow(page)
  await page.setViewportSize({ width: 1280, height: 900 })
  state.expired = true
  await page.getByText('排行榜与抽奖', { exact: true }).click()
  await page.getByRole('heading', { name: '登录现场管理台' }).waitFor()
  assert.equal(await page.evaluate(() => localStorage.getItem('flipbelt_admin_token')), null)
  assert.equal(await page.getByText('活动概览', { exact: true }).count(), 0)
  await page.setViewportSize({ width: 375, height: 667 })
  await assertNarrow(page)
  await capture(page, 'admin-login')
  assert.deepEqual(errors, [])
  checks += 5
  await context.close()
}
try {
  for (const engine of ['chromium', 'webkit']) {
    const browser = await playwright[engine].launch(engine === 'chromium' ? { channel: 'chrome' } : {})
    try {
      await runMobile(browser, engine)
      if (engine === 'chromium') await runAdmin(browser)
      console.log(engine + ': mobile recovery/layout' + (engine === 'chromium' ? ' and admin authentication' : '') + ' passed')
    } finally { await browser.close() }
  }
  console.log('UI checks passed: ' + checks + ' assertions/groups; isolated fixtures only')
} finally { await new Promise(resolve => server.close(resolve)) }
