const assets = {
  xiaohongshuQr: '../../assets/小红书二维码测试版.png',
  douyinQr: '../../assets/抖音二维码测试版.png',
  demoVideo: '../../assets/袋鼠裤.mp4',
  scorePoster: '../../assets/image.png',
  rewardPoster: '../../assets/image2.png'
}

const steps = [
  {
    caption: '第 1 步 · 先完成关注', short: '关注确认', tag: '现场工作人员确认', title: '关注品牌账号',
    copy: '扫描现场二维码，完成小红书和抖音关注后，向工作人员出示。', swipe: true,
    content: () => `<div class="qr-row"><figure class="qr-tile"><img src="${assets.xiaohongshuQr}" alt="小红书测试二维码"><figcaption>小红书</figcaption></figure><figure class="qr-tile"><img src="${assets.douyinQr}" alt="抖音测试二维码"><figcaption>抖音</figcaption></figure></div><div class="micro-list"><span>现场二维码为主入口，页面二维码可长按识别</span><span>关注完成后，由工作人员现场确认</span></div>`,
    action: '已向工作人员出示，继续报名'
  },
  {
    caption: '第 2 步 · 领取号码牌', short: '填写报名', tag: '只需提交一次', title: '填写参赛信息',
    copy: '填写姓名、手机号和工作人员发放的号码牌。号码牌由你自行保留。', swipe: false,
    content: () => `<form id="register-form" class="form-grid" novalidate><label>姓名<input name="name" placeholder="请输入姓名" autocomplete="name"></label><label>手机号<input name="phone" inputmode="numeric" placeholder="请输入手机号"></label><label>参赛号码牌<input name="number" placeholder="例如：A018"></label></form><div class="micro-list"><span>提交后不可重复报名</span><span>本页为 FP 演示，不会保存真实资料</span></div>`,
    action: '提交报名，查看挑战规则'
  },
  {
    caption: '第 3 步 · 上场前看一遍', short: '挑战准备', tag: '规则、奖品与示范', title: '准备开始挑战',
    copy: '40 秒内完成装载；工作人员会根据有效道具数量登记成绩。', swipe: true,
    content: () => `<div class="media-row"><video class="demo-video" src="${assets.demoVideo}" controls playsinline preload="metadata"></video><div class="poster-stack"><img src="${assets.scorePoster}" alt="能装规则与计分表"><img src="${assets.rewardPoster}" alt="得分排名与活动奖励"></div></div><div class="micro-list"><span>挑战规则与计分方式</span><span>奖励区间、活动奖品与示范视频</span></div>`,
    action: '我已了解，去现场挑战'
  },
  {
    caption: '第 4 步 · 线下现场完成', short: '现场挑战', tag: '等待工作人员录分', title: '告诉工作人员你的号码牌',
    copy: '现场完成挑战后，工作人员会录入每种有效道具数量，系统自动计算成绩。', swipe: false,
    content: () => `<div class="status-box"><strong><span class="status-dot"></span>当前状态：等待成绩登记</strong>每人仅可挑战一次；挑战结束后道具掉落不计分。工作人员登记完成后，这张卡会自动进入成绩页。</div><div class="micro-list"><span>40 秒内完成装载，超时不计分</span><span>请保留自己的号码牌，方便工作人员查询</span></div>`,
    action: 'FP 演示：模拟工作人员已录分', demoOnly: true
  },
  {
    caption: '第 5 步 · 成绩与排名', short: '查看成绩', tag: '工作人员已登记', title: '你的挑战成绩',
    copy: '这是纯前端演示数据。正式接入后，成绩、排名与奖励均来自后台。', swipe: false,
    content: () => `<div class="result-score"><b>45</b><span>分</span></div><div class="rank-box"><span>当前排名</span><b>第 12 名</b></div><div class="micro-list" style="margin-top:12px"><span>即时奖励：运动短袜</span><span>已达到最终抽奖门槛，可扫码进入微信群</span></div>`,
    action: '刷新模拟成绩'
  }
]

let current = 0
let completed = 0
let swipeStartY = 0
let swipeStartX = 0
let dragCard = null
let dragging = false

const deck = document.getElementById('deck')
const doneCount = document.getElementById('done-count')
const stepCaption = document.getElementById('step-caption')
const historyButton = document.getElementById('history-button')
const historyPanel = document.getElementById('history-panel')
const progressDots = document.getElementById('progress-dots')
const historyStack = document.getElementById('history-stack')

function cardTemplate(step, layer) {
  const tone = ['tone-slate', 'tone-purple', 'tone-teal', 'tone-pink', 'tone-yellow'][(current + layer) % 5]
  if (layer > 0) {
    return `<article class="flow-card ${tone} ${layer === 1 ? 'middle' : 'back'} ghost-card" aria-hidden="true"><span class="ghost-number">下一步 · ${current + layer + 1}</span><h2>${step.title}</h2><p>${step.copy}</p></article>`
  }
  const tip = step.swipe ? '上滑这张卡，也可以完成并收起' : step.demoOnly ? '真实活动中仅由工作人员录分后进入下一步' : current === steps.length - 1 ? '已到达流程最后一步' : '填写完成后，点击按钮提交并进入下一步'
  return `<article class="flow-card ${tone} front" data-front-card><div><div class="card-topline"><span class="step-badge">${step.tag}</span><span class="step-index">${current + 1} / ${steps.length}</span></div><h2 class="card-title">${step.title}</h2><p class="card-copy">${step.copy}</p>${step.content()}</div><div><button id="card-action" class="card-action ${step.demoOnly ? 'secondary' : ''}" type="button">${step.action}</button><p id="action-error" class="error"></p><p class="swipe-tip">${tip}</p></div></article>`
}

function renderHistory() {
  historyPanel.replaceChildren()
  steps.slice(0, completed).forEach((step, index) => {
    const chip = document.createElement('button')
    chip.className = 'history-chip'
    chip.type = 'button'
    chip.textContent = `✓ ${index + 1}. ${step.short}`
    chip.addEventListener('click', () => previewHistory(index))
    historyPanel.appendChild(chip)
  })
  const currentChip = document.createElement('button')
  currentChip.className = 'history-chip current'
  currentChip.type = 'button'
  currentChip.disabled = true
  currentChip.textContent = `当前：${current + 1}. ${steps[current].short}`
  historyPanel.appendChild(currentChip)
}

function renderHistoryStack() {
  historyStack.replaceChildren()
  const visibleCards = Math.min(completed, 3)
  for (let index = 0; index < visibleCards; index += 1) historyStack.appendChild(document.createElement('i'))
}

function previewHistory(index) {
  const item = steps[index]
  window.alert(`已完成步骤：${index + 1}. ${item.short}\n\n${item.title}\n${item.copy}\n\n历史查看不会撤销报名或挑战记录。`)
}

function render() {
  const currentStep = steps[current]
  stepCaption.textContent = currentStep.caption
  doneCount.textContent = String(completed)
  deck.innerHTML = [0, 1, 2].map((offset) => steps[current + offset] ? cardTemplate(steps[current + offset], offset) : '').join('')
  progressDots.innerHTML = steps.map((_, index) => `<span class="${index <= completed ? 'active' : ''}"></span>`).join('')
  renderHistory()
  renderHistoryStack()
  const action = document.getElementById('card-action')
  if (action) action.addEventListener('click', () => requestAdvance('button'))
}

function validRegistration() {
  const form = document.getElementById('register-form')
  if (!form) return true
  const values = [...form.querySelectorAll('input')].map((input) => input.value.trim())
  if (values.every(Boolean)) return true
  document.getElementById('action-error').textContent = '请先完整填写三项信息（仅作前端演示，不会提交）。'
  return false
}

function requestAdvance(source) {
  if (current === steps.length - 1) {
    document.getElementById('action-error').textContent = '模拟成绩已是最新状态。'
    return
  }
  if (current === 1 && !validRegistration()) return
  if (source === 'swipe' && !steps[current].swipe) return
  completeCurrent()
}

function completeCurrent() {
  const front = deck.querySelector('[data-front-card]')
  if (!front) return
  dragging = false
  deck.classList.remove('is-dragging')
  historyStack.classList.remove('is-target')
  front.classList.remove('is-dragging')
  front.style.transform = ''
  front.style.opacity = ''
  window.requestAnimationFrame(() => {
    front.classList.add('completing')
    window.setTimeout(() => {
      completed = Math.max(completed, current + 1)
      current += 1
      render()
    }, 400)
  })
}

historyButton.addEventListener('click', () => {
  const open = historyPanel.classList.toggle('open')
  historyButton.setAttribute('aria-expanded', String(open))
})

function beginDrag(clientX, clientY, target) {
  if (dragging || target.closest('button, input, video')) return
  if (!steps[current].swipe) return
  dragCard = deck.querySelector('[data-front-card]')
  if (!dragCard) return
  swipeStartY = clientY
  swipeStartX = clientX
  dragging = true
  dragCard.classList.add('is-dragging')
  deck.classList.add('is-dragging')
  historyStack.classList.add('is-target')
}

function moveDrag(clientX, clientY) {
  if (!dragging || !dragCard) return
  const deltaX = clientX - swipeStartX
  const deltaY = Math.min(34, clientY - swipeStartY)
  const progress = Math.min(1, Math.max(0, -deltaY / 210))
  const scale = 1 - progress * .58
  const rotate = deltaX * .04 + progress * 7
  dragCard.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 45px) scale(${scale}) rotate(${rotate}deg)`
  dragCard.style.opacity = String(1 - progress * .18)
}

function cancelDrag() {
  if (!dragging || !dragCard) return
  dragging = false
  deck.classList.remove('is-dragging')
  historyStack.classList.remove('is-target')
  dragCard.classList.remove('is-dragging')
  dragCard.style.transform = ''
  dragCard.style.opacity = ''
  dragCard = null
}

function endDrag(clientX, clientY) {
  if (!dragging) return
  const upDistance = swipeStartY - clientY
  const rightDistance = clientX - swipeStartX
  if (upDistance > 92 || (upDistance > 48 && rightDistance > 46)) completeCurrent()
  else cancelDrag()
  swipeStartY = 0
  dragCard = null
}

deck.addEventListener('pointerdown', (event) => { beginDrag(event.clientX, event.clientY, event.target); deck.setPointerCapture(event.pointerId) })
deck.addEventListener('pointermove', (event) => moveDrag(event.clientX, event.clientY))
deck.addEventListener('pointerup', (event) => endDrag(event.clientX, event.clientY))
deck.addEventListener('pointercancel', cancelDrag)
deck.addEventListener('mousedown', (event) => beginDrag(event.clientX, event.clientY, event.target))
window.addEventListener('mousemove', (event) => moveDrag(event.clientX, event.clientY))
window.addEventListener('mouseup', (event) => endDrag(event.clientX, event.clientY))
deck.addEventListener('touchstart', (event) => { const touch = event.touches[0]; if (touch) beginDrag(touch.clientX, touch.clientY, event.target) }, { passive: true })
deck.addEventListener('touchmove', (event) => { const touch = event.touches[0]; if (dragging && touch) { event.preventDefault(); moveDrag(touch.clientX, touch.clientY) } }, { passive: false })
deck.addEventListener('touchend', (event) => { const touch = event.changedTouches[0]; if (touch) endDrag(touch.clientX, touch.clientY); else cancelDrag() })
deck.addEventListener('touchcancel', cancelDrag)

render()
