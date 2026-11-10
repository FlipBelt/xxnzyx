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
    width: window.innerWidth,
    scroll: Math.max(document.documentElement.scrollWidth, document.querySelector('.taro_page_show')?.scrollWidth ?? 0),
    bodyOverflow: document.body.style.overflow, htmlOverflow: document.documentElement.style.overflow
  }))
  assert.ok(sizes.scroll <= sizes.width + 1, JSON.stringify(sizes))
  assert.notEqual(sizes.bodyOverflow, 'hidden')
  assert.notEqual(sizes.htmlOverflow, 'hidden')
  checks += 1
}
async function fixture(page, { initialFailures = 0, loseFirstReceipt = false, mobileAdmin = false } = {}) {
  const state = { activityReads: 0, posts: 0, records: 0, meReads: 0, profileReady: false, expired: false }
  state.publicActivity = activity
  state.activityUnavailable = false
  state.activityUrls = []
  const admin = { id: 1, username: 'fixture-admin', display_name: '本地测试管理员', role: 'admin' }
  const testItems = ['隐藏奖励', '轻薄衣物', '登山杖', '水壶', '耳机', '手机型号', '能量胶', '盐丸'].map((name, index) => ({
    id: index + 1, code: `fixture_${index}`, name, points: index === 3 ? 5 : 2, max_quantity: [null, 2, 1, 1, 1, 1, 20, 20][index]
  }))
  const adminActivity = { ...activity, rules_version: '1'.repeat(64), score_items: testItems,
    reward_tiers: [{ id: 1, min_score: 0, max_score: 30, title: '起步', prize_name: '示例奖品' }, { id: 2, min_score: 31, max_score: null, title: '领先', prize_name: '示例奖品' }] }
  const entrants = Array.from({ length: 10 }, (_, index) => ({
    id: index + 1, activity_id: 1, name: '合成选手', phone: '138000000' + String(index).padStart(2, '0'),
    number_plate: `F${String(index + 1).padStart(2, '0')}`, registered_at: index < 2 ? '2026-11-08T16:15:00Z' : '2026-11-08T15:45:00Z',
    status: 'registered', score: null, score_details: [], score_version: null
  }))
  const receipts = new Map()
  state.scoreWrites = 0
  state.loseScoreReceipt = mobileAdmin
  state.rejectConflict = false
  state.homePreviewScore = 7
  state.failHomeRanking = false
  await page.route('**/flipbelt-api/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const endpoint = url.pathname.split('/api/v1')[1]
    const json = (data, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) })
    if (endpoint === '/activity/current') {
      state.activityReads += 1
      state.activityUrls.push(url.href)
      return state.activityUnavailable || state.activityReads <= initialFailures
        ? json({ detail: '测试网络暂不可用' }, 503) : json(state.publicActivity)
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
      return json({ access_token: 'synthetic-admin-token', admin })
    }
    if (endpoint.startsWith('/admin/')) {
      if (state.expired) return json({ detail: '登录状态无效' }, 401)
      assert.equal(route.request().headers().authorization, 'Bearer synthetic-admin-token')
      if (endpoint === '/admin/me') return json(admin)
      if (endpoint === '/admin/dashboard') return json({ activity, registered_count: 1, scored_count: 0, pending_score_count: 1, draw_qualified_count: 0, highest_score: 0 })
      if (endpoint === '/admin/config') return json(mobileAdmin ? adminActivity : activity)
      if (endpoint === '/admin/leaderboard') {
        if (state.failHomeRanking && url.searchParams.get('limit') === '10') return json({ detail: '测试网络不可用' }, 503)
        return json({ entries: mobileAdmin ? [{ ...entrants[0], registration_id: 1, rank: 1, score: state.homePreviewScore, title: '起步' }] : [] })
      }
      if (endpoint === '/admin/draw/candidates') return json({ threshold: 45, items: [] })
      if (endpoint === '/admin/draw/result') return json({ already_drawn: false, results: [] })
      if (endpoint === '/admin/registrations' && route.request().method() === 'POST') {
        const row = { ...route.request().postDataJSON(), id: 20, activity_id: 1, registered_at: '2026-11-08T16:15:00Z', score: null, score_details: [], score_version: null }
        entrants.push(row)
        return json(row, 201)
      }
      if (endpoint === '/admin/registrations') {
        const keyword = url.searchParams.get('keyword') ?? ''
        const items = mobileAdmin ? entrants.filter((row) => url.searchParams.has('pending_only') ? row.score == null : row.number_plate.includes(keyword)) : []
        return json({ items, has_more: false })
      }
      if (endpoint.startsWith('/admin/registrations/')) return json(entrants.find((row) => row.id === Number(endpoint.split('/').at(-1))))
      if (endpoint === '/admin/score-submissions') {
        const draft = route.request().postDataJSON()
        if (receipts.has(draft.operation_id)) return json(receipts.get(draft.operation_id))
        const row = entrants.find((entry) => entry.id === draft.registration_id)
        if (state.rejectConflict) {
          state.rejectConflict = false
          row.score_version = 'updated-elsewhere'
          row.score = 5
        }
        if (draft.expected_version !== row.score_version) return json({ detail: '这位选手的成绩已更新，请核对后保存' }, 409)
        const details = draft.items.map((item) => ({ ...item, subtotal: testItems[item.score_item_id - 1].points * item.quantity }))
        const receipt = { id: row.id, registration_id: row.id, version: draft.operation_id, total_score: details.reduce((total, item) => total + item.subtotal, 0), details }
        Object.assign(row, { score: receipt.total_score, score_details: details, score_version: receipt.version })
        receipts.set(draft.operation_id, receipt)
        state.scoreWrites++
        if (state.loseScoreReceipt) { state.loseScoreReceipt = false; return route.abort('failed') }
        return json(receipt)
      }
      if (endpoint.startsWith('/admin/score-submissions/')) return json({ receipt: receipts.get(endpoint.split('/').at(-1)) ?? null })
    }
    return json({ detail: '未定义测试响应' }, 404)
  })
  return state
}
async function runMobile(browser, engine) {
  for (const [width, height] of [[320, 568], [390, 844], [430, 932]]) {
    const reduceMotion = engine === 'webkit' && width === 320
    const context = await browser.newContext({
      viewport: { width, height }, isMobile: true, hasTouch: true,
      reducedMotion: reduceMotion ? 'reduce' : 'no-preference',
      userAgent: engine === 'webkit' ? playwright.devices['iPhone 13'].userAgent : playwright.devices['Pixel 7'].userAgent
    })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    const state = await fixture(page, { loseFirstReceipt: true })
    await page.goto(origin)
    await page.locator('.brand-logo img').waitFor()
    await page.waitForFunction(() => document.querySelector('.brand-logo img')?.naturalWidth > 0)
    await assertNarrow(page)
    if (width === 390) {
      await page.waitForFunction(() => {
        const logos = [...document.querySelectorAll('.platform-logo img')]
        return logos.length === 2 && logos.every(logo => logo.naturalWidth > 0)
      })
      for (const [label, title] of [['抖音二维码', '抖音'], ['淘宝店铺二维码', '淘宝店铺']]) {
        const trigger = page.getByRole('button', { name: label })
        await trigger.press('Enter')
        await page.getByText(title, { exact: true }).and(page.locator('.follow-dialog__title')).waitFor()
        await page.waitForFunction(() => document.activeElement?.matches('.follow-dialog__close'), undefined, { timeout: 5000 })
        await page.keyboard.press('Escape')
        await page.locator('.follow-dialog').waitFor({ state: 'hidden' })
        assert.ok(await trigger.evaluate(node => node === document.activeElement))
      }
      await capture(page, engine + '-race-home')
      checks += 3
    }
    checks += 1
    if (width === 390) await page.getByRole('button', { name: '下一步：填写报名' }).press('Enter')
    else await page.getByText('下一步：填写报名', { exact: true }).click()
    await page.getByText('填写参赛信息', { exact: true }).waitFor()
    await assertNarrow(page)
    for (const [placeholder, value] of [['请输入姓名', '本地测试选手'], ['请输入11位手机号', '13900000001'], ['请输入本场参赛号码牌', 'LOCAL-07']]) {
      const input = page.getByPlaceholder(placeholder)
      await input.fill(value)
      await page.setViewportSize({ width, height: 330 })
      await input.scrollIntoViewIfNeeded()
      await assertNarrow(page)
      const box = await input.boundingBox()
      assert.ok(box && box.x >= -1 && box.x + box.width <= width + 1 && box.height >= 44)
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
    if (width <= 390) {
      const currentStop = page.locator('.race-stop[aria-current="step"]')
      const assertStop = async label => assert.ok((await currentStop.innerText()).endsWith(label))
      await assertStop('备战')
      await page.getByText('下一步：查看计分与奖励', { exact: true }).click()
      await page.getByText('计分与奖励', { exact: true }).first().waitFor()
      await assertStop('备战')
      await assertNarrow(page)
      await page.getByText('下一步：查看挑战规则', { exact: true }).click()
      await page.getByText('挑战规则', { exact: true }).first().waitFor()
      await assertNarrow(page)
      if (width === 390) await capture(page, engine + '-race-rules')
      await page.getByText('下一步：进入现场挑战', { exact: true }).click()
      await page.getByText('LOCAL-07', { exact: true }).and(page.locator('.race-bib__number')).waitFor()
      await assertStop('挑战')
      if (width === 390) await capture(page, engine + '-race-bib')
      await page.getByText('刷新我的成绩', { exact: true }).click()
      await page.getByText('成绩加载失败，请联系工作人员。', { exact: true }).waitFor()
      state.profileReady = true
      await page.getByText('刷新我的成绩', { exact: true }).click()
      await page.getByText('我的挑战成绩', { exact: true }).waitFor()
      await assertStop('成绩')
      assert.match(await page.locator('.result-score').innerText(), /50/)
      const animation = await page.locator('.result-score-panel').evaluate(node => getComputedStyle(node).animationName)
      assert.equal(animation, reduceMotion ? 'none' : 'score-arrival')
      await page.waitForFunction(() => document.querySelector('img.draw-qr')?.naturalWidth > 0)
      await assertNarrow(page)
      if (width === 390) await capture(page, engine + '-race-result')
      checks += 10
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
async function runRuleSync(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const state = await fixture(page)
  const tiers = (cutoff, prize) => [
    { id: 1, min_score: 0, max_score: cutoff - 1, title: '起步', prize_name: '测试冰巾' },
    { id: 2, min_score: cutoff, max_score: null, title: '领先', prize_name: prize },
  ]
  state.publicActivity = { ...activity, reward_tiers: tiers(50, '旧奖品') }
  await page.clock.install()
  await page.goto(origin + '/flipbelt/')
  await page.getByText('下一步：填写报名', { exact: true }).click()
  await page.getByPlaceholder('请输入姓名').fill('合成选手')
  await page.getByPlaceholder('请输入11位手机号').fill('13900000001')
  await page.getByPlaceholder('请输入本场参赛号码牌').fill('RULES-01')
  await page.getByText('提交报名并继续', { exact: true }).click()
  const rulesRead = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith('/activity/current'))
  await page.getByText('下一步：查看计分与奖励', { exact: true }).click()
  assert.equal((await rulesRead).status(), 200)
  await page.getByText('50分以上', { exact: true }).waitFor()
  assert.equal(state.activityReads, 2)
  assert.notEqual(state.activityUrls[0], state.activityUrls[1])

  state.publicActivity = { ...activity, reward_tiers: tiers(56, '新奖品') }
  await page.clock.fastForward(15_000)
  await page.getByText('56分以上', { exact: true }).waitFor()
  await page.getByText('0–55分', { exact: true }).waitFor()
  await page.getByText('新奖品', { exact: true }).waitFor()
  assert.equal(await page.getByText('50分以上', { exact: true }).count(), 0)

  state.activityUnavailable = true
  await page.evaluate(() => window.dispatchEvent(new Event('pageshow')))
  await page.getByText('暂时无法核对最新规则，当前显示上次读取的内容。', { exact: true }).waitFor()
  assert.equal(await page.getByText('56分以上', { exact: true }).count(), 1)
  state.activityUnavailable = false
  state.publicActivity = { ...activity, reward_tiers: [] }
  await page.getByText('刷新规则', { exact: true }).click()
  await page.getByText('暂无奖励区间。', { exact: true }).waitFor()
  assert.equal(await page.getByText('50分以上', { exact: true }).count(), 0)

  const publishedRuleText = '由后台保存的说明。\n现场以工作人员核对为准。'
  state.publicActivity = { ...activity, rules_text: publishedRuleText, reward_tiers: tiers(56, '新奖品'), score_items: [
    { id: 3, code: 'phone_model', name: '后台更名道具', points: 8, max_quantity: 2, is_required: true },
    { id: 4, code: 'hidden_bonus', name: '隐藏道具', points: 7, max_quantity: 1, is_hidden_bonus: true, appear_at_seconds_remaining: 3 },
  ] }
  await page.getByText('下一步：查看挑战规则', { exact: true }).click()
  await page.locator('.published-rule-text').filter({ hasText: '由后台保存的说明。' }).waitFor()
  assert.equal(await page.locator('.published-rule-text').innerText(), publishedRuleText)
  await page.getByText('后台更名道具', { exact: true }).waitFor()
  await page.getByText('8分/个', { exact: true }).waitFor()
  await page.getByText('必须项 · 最多2个', { exact: true }).waitFor()
  await page.getByText('最多1个 · 最后3秒出现', { exact: true }).waitFor()
  await assertNarrow(page)

  await page.goto(origin + '/flipbelt/#/pages/rules/index')
  await page.getByText('56分以上', { exact: true }).waitFor()
  assert.equal(await page.locator('.published-rule-text').innerText(), publishedRuleText)
  state.publicActivity = { ...state.publicActivity, rules_text: '更新后的公示文案。', reward_tiers: tiers(60, '独立页更新奖品') }
  await page.clock.fastForward(15_000)
  await page.getByText('60分以上', { exact: true }).waitFor()
  assert.equal(await page.locator('.published-rule-text').innerText(), '更新后的公示文案。')
  assert.deepEqual(errors, [])
  checks += 15
  await context.close()
}
async function runAdmin(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const state = await fixture(page, { mobileAdmin: true })
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
  await page.getByRole('button', { name: '开始录分' }).click()
  await page.locator('.pending-day').first().getByText('F01', { exact: true }).waitFor()
  await page.locator('.pending-day').last().getByText('F03', { exact: true }).waitFor()
  await page.getByRole('navigation', { name: '后台导航' }).getByText('现场概况', { exact: true }).click()
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
  checks += 7
  await context.close()
}
async function runMobileAdmin(browser, engine) {
  const context = await browser.newContext({ viewport: { width: 390, height: 620 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  const state = await fixture(page, { mobileAdmin: true })
  await page.clock.install()
  await page.goto(origin + '/flipbelt-admin/')
  await page.locator('input').nth(0).fill('fixture-admin')
  await page.locator('input').nth(1).fill('local-ui-password')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  const homeRanking = page.getByRole('region', { name: '实时排行榜' })
  await homeRanking.getByText('7 分', { exact: true }).waitFor()
  state.homePreviewScore = 9
  await page.clock.fastForward(10_000)
  await homeRanking.getByText('9 分', { exact: true }).waitFor()
  state.failHomeRanking = true
  await page.clock.fastForward(10_000)
  await homeRanking.getByText('刷新失败，显示上次成功榜单').waitFor()
  assert.equal(await homeRanking.getByText('9 分', { exact: true }).count(), 1)
  state.failHomeRanking = false
  await page.getByRole('button', { name: '开始录分' }).click()
  const queue = page.getByRole('region', { name: '待录分名单' })
  await queue.getByRole('heading', { name: /2026[/年-]11[/月-]09/ }).waitFor()
  await queue.getByRole('heading', { name: /2026[/年-]11[/月-]08/ }).waitFor()
  assert.equal(await queue.locator('.pending-day').first().getByRole('button', { name: /#F01.*录分/ }).count(), 1)
  assert.equal(await queue.locator('.pending-day').last().getByRole('button', { name: /#F03.*录分/ }).count(), 1)
  const lookup = page.getByRole('searchbox', { name: '查找参赛者' })
  const select = async (plate) => {
    await lookup.fill(plate)
    await lookup.press('Enter')
    await page.getByRole('button', { name: new RegExp(`#${plate}.*录分`) }).click()
  }
  const navigate = async (name) => {
    await page.getByRole('button', { name: '菜单' }).click()
    await page.getByRole('navigation', { name: '手机后台导航' }).getByRole('button', { name }).click()
  }
  const checkForm = async () => {
    await assertNarrow(page)
    const overflow = await page.locator('main.content, .mobile-score-items, .mobile-settings, .mobile-list').evaluateAll((nodes) =>
      nodes.filter((node) => node.scrollWidth > node.clientWidth + 1).map((node) => node.className))
    assert.deepEqual(overflow, [])
    assert.equal(await page.locator('.sidebar').isVisible(), false)
    assert.equal(await page.locator('.el-table').count(), 0)
    checks += 3
  }

  await select('F01')
  assert.equal(await page.locator('.mobile-score-row').count(), 8)
  await checkForm()
  const last = await page.locator('.mobile-score-row').last().boundingBox()
  const footer = await page.locator('.mobile-score-footer').boundingBox()
  assert.ok(last.y + last.height <= footer.y + 1 && footer.y + footer.height <= 620, JSON.stringify({ last, footer }))
  await capture(page, `${engine}-mobile-admin-score`)
  await page.getByRole('button', { name: '计入水壶' }).click()
  const quantity = page.getByRole('textbox', { name: '能量胶' })
  await quantity.fill('21')
  await page.getByText('请输入 0–20 的整数').waitFor()
  await quantity.fill('1')
  await page.setViewportSize({ width: 390, height: 330 })
  assert.equal(await page.locator('.mobile-score-footer').evaluate((element) => getComputedStyle(element).position), 'static')
  await quantity.press('Enter')
  await page.setViewportSize({ width: 390, height: 620 })
  await page.getByRole('button', { name: '保存并录下一位' }).click()
  await page.getByText('保存结果待确认，联网后可查保存结果').waitFor()
  assert.equal(state.scoreWrites, 1)
  await page.getByRole('button', { name: '保留待确认，查下一位' }).click()
  await select('F02')
  await context.setOffline(true)
  await page.getByRole('button', { name: '离线 · 未提交' }).waitFor()
  const lateReceipt = page.waitForResponse((response) => response.url().includes('/admin/score-submissions/1/'))
  await context.setOffline(false)
  await lateReceipt
  await page.getByRole('heading', { name: '#F02' }).waitFor()
  await page.reload()
  await page.getByRole('button', { name: '开始录分' }).click()
  await page.getByText('待处理 1').click()
  await page.getByRole('button', { name: /保存待确认 · 查结果|已保存 · 查看/ }).click()
  await page.getByText('#F01 已保存 · 7 分').waitFor()
  assert.equal(state.scoreWrites, 1)
  assert.equal(await lookup.inputValue(), '')

  for (let index = 2; index <= 10; index++) {
    const plate = `F${String(index).padStart(2, '0')}`
    await select(plate)
    if (index === 10) {
      await page.getByRole('button', { name: '保存 0 分' }).click()
      await page.getByRole('dialog').getByRole('button', { name: '保存 0 分' }).click()
      await page.getByText(`#${plate} 已保存 · 0 分`).waitFor()
      continue
    }
    await page.getByRole('button', { name: '计入水壶' }).click()
    if (index === 2) {
      state.rejectConflict = true
      await page.getByRole('button', { name: '保存并录下一位' }).click()
      await page.getByText('核对服务器记录和本机录入').waitFor()
      await page.getByRole('button', { name: '已核对，继续编辑' }).click()
    }
    await page.getByRole('button', { name: '保存并录下一位' }).click()
    await page.getByText(`#${plate} 已保存 · 5 分`).waitFor()
  }
  assert.equal(state.scoreWrites, 10)
  await queue.getByText('当前没有待录分人员。', { exact: true }).waitFor()
  for (const width of [320, 375, 430]) { await page.setViewportSize({ width, height: 620 }); await checkForm() }
  await page.setViewportSize({ width: 320, height: 568 })
  await navigate('补录报名')
  await page.getByLabel('号码牌', { exact: true }).fill('NEW-20')
  await page.getByLabel('姓名', { exact: true }).fill('合成补录')
  await page.getByLabel('手机号', { exact: true }).fill('13700000020')
  await page.getByRole('button', { name: '保存并去录分' }).click()
  await page.getByRole('heading', { name: '#NEW-20' }).waitFor()
  await checkForm()

  await navigate('活动设置')
  await page.getByRole('button', { name: /奖励区间/ }).click()
  await page.getByRole('button', { name: /0–30 分/ }).click()
  await page.getByLabel('最高分', { exact: true }).fill('25')
  await page.getByRole('button', { name: '保存奖励区间' }).click()
  await page.getByText('请检查区间是否从 0 分连续排列，且只有最后一档可以无上限').waitFor()
  await checkForm()
  await capture(page, `${engine}-mobile-admin-settings`)
  await page.getByRole('button', { name: '‹ 设置' }).click()
  await page.getByRole('button', { name: '放弃修改' }).click()
  await page.getByRole('button', { name: /计分道具/ }).click()
  await page.getByRole('button', { name: /水壶/ }).click()
  await page.getByLabel('分值', { exact: true }).waitFor()
  await checkForm()
  await navigate('排行榜')
  await page.getByText('#F01', { exact: true }).waitFor()
  await page.getByRole('button', { name: '最终抽奖' }).click()
  await page.getByText('符合资格的选手不足两人。').waitFor()
  assert.ok(await page.getByRole('button', { name: '随机抽取两位获奖者' }).isDisabled())
  await checkForm()
  assert.deepEqual(errors, [])
  checks += 23
  await context.close()
}
try {
  for (const engine of ['chromium', 'webkit']) {
    const browser = await playwright[engine].launch(engine === 'chromium' ? { channel: 'chrome' } : {})
    try {
      if (process.env.UI_ADMIN_ONLY !== '1') {
        await runMobile(browser, engine)
        await runRuleSync(browser)
      }
      if (process.env.UI_PARTICIPANT_ONLY !== '1') {
        if (engine === 'chromium') await runAdmin(browser)
        await runMobileAdmin(browser, engine)
      }
      console.log(engine + ': UI checks passed')
    } finally { await browser.close() }
  }
  console.log('UI checks passed: ' + checks + ' assertions/groups; isolated fixtures only')
} finally { await new Promise(resolve => server.close(resolve)) }
