<template>
  <el-container class="admin-layout">
    <el-aside class="sidebar" width="256px">
      <div class="admin-logo"><span class="logo-mark">FB</span><div><strong>FLIPBELT</strong><small>40秒能装挑战 · 管理台</small></div></div>
      <nav aria-label="后台导航">
        <el-menu :default-active="section" @select="changeSection">
          <el-menu-item index="dashboard"><el-icon><Odometer /></el-icon><span>现场概况</span></el-menu-item>
          <el-menu-item index="supplement"><el-icon><UserFilled /></el-icon><span>补录报名</span></el-menu-item>
          <el-menu-item index="score"><el-icon><EditPen /></el-icon><span>登记成绩</span></el-menu-item>
          <el-menu-item index="ranking"><el-icon><Trophy /></el-icon><span>排行榜与抽奖</span></el-menu-item>
          <el-menu-item index="settings"><el-icon><Setting /></el-icon><span>活动设置</span></el-menu-item>
        </el-menu>
      </nav>
      <div class="sidebar-footer"><span class="status-dot"></span>活动数据实时保存</div>
    </el-aside>
    <el-container class="main-area">
      <el-header class="topbar">
        <div><p class="eyebrow">活动运营</p><h1>{{ heading }}</h1></div>
        <div class="topbar-actions">
          <el-input v-model="globalSearch" class="top-search" placeholder="搜索姓名、手机或号码牌" clearable @keyup.enter="searchFromTop"><template #prefix><el-icon><Search /></el-icon></template></el-input>
          <el-button class="icon-button" circle aria-label="通知"><el-icon><Bell /></el-icon></el-button>
          <div class="user-chip"><el-icon><UserFilled /></el-icon><span>管理员</span></div>
          <span class="direct-access">现场直入模式</span>
        </div>
      </el-header>
      <el-main class="content">
        <template v-if="section === 'dashboard' && dashboard">
          <section class="page-intro"><div><h2>活动概览</h2><p>{{ config?.title || '40秒能装挑战' }} · 现场进度与待办一目了然</p></div><el-button class="primary-button" @click="changeSection('score')"><el-icon><EditPen /></el-icon>开始录分</el-button></section>
          <section class="kpi-grid" aria-label="活动关键数据">
            <article v-for="stat in stats" :key="stat.label" class="kpi-card"><div><p>{{ stat.label }}</p><strong>{{ stat.value }}</strong><small>{{ stat.hint }}</small></div><span :class="['kpi-icon', stat.tone]"><el-icon><component :is="stat.icon" /></el-icon></span></article>
          </section>
          <section class="dashboard-grid">
            <article class="panel progress-panel"><header><div><h3>现场进度</h3><p>按当前报名与成绩登记数据统计</p></div><span class="panel-badge">实时</span></header>
              <div v-for="item in dashboardBars" :key="item.label" class="progress-row"><div class="progress-label"><span>{{ item.label }}</span><strong>{{ item.value }}<small>{{ item.suffix }}</small></strong></div><el-progress :percentage="item.percentage" :show-text="false" :stroke-width="9" :color="item.color" /></div>
            </article>
            <aside class="panel status-panel"><header><div><h3>现场状态</h3><p>重要信息提示</p></div></header><ul><li><span class="status-dot"></span><div><strong>挑战限额</strong><p>每人仅可挑战 1 次</p></div></li><li><span class="status-dot warning"></span><div><strong>待登记成绩</strong><p>{{ dashboard.pending_score_count }} 位参赛者等待录分</p></div></li><li><span class="status-dot"></span><div><strong>最终抽奖</strong><p>{{ config?.draw_threshold ?? 45 }} 分以上可参与抽取</p></div></li></ul></aside>
          </section>
          <section class="panel workflow-panel"><header><div><h3>现场操作流程</h3><p>按顺序推进，活动数据会自动保存</p></div></header><el-steps :active="1" finish-status="success" align-center><el-step title="用户扫码报名" description="填写姓名、手机与号码牌" /><el-step title="工作人员登记成绩" description="录入各类道具数量" /><el-step title="用户查看排名奖励" description="扫码查询实时积分" /><el-step title="结束后执行抽奖" description="符合门槛者参与抽取" /></el-steps></section>
        </template>

        <template v-if="section === 'supplement'">
          <section class="page-intro"><div><h2>补录报名</h2><p>用于现场网络异常或资料未成功保存时，补齐参赛者资料后直接录入成绩。</p></div></section>
          <section class="panel supplement-panel"><header><div><h3>补录参赛者</h3><p>手机号和号码牌不能与本场已有记录重复。</p></div></header><el-alert title="补录后会进入正常参赛名单，和用户扫码报名的数据完全一致。" type="info" :closable="false" show-icon /><el-form class="settings-form supplement-form" label-position="top" @submit.prevent="createSupplement"><el-form-item label="姓名"><el-input v-model="supplementForm.name" placeholder="请输入姓名" maxlength="80" /></el-form-item><el-form-item label="手机号"><el-input v-model="supplementForm.phone" placeholder="请输入11位手机号" maxlength="11" /></el-form-item><el-form-item label="参赛号码牌"><el-input v-model="supplementForm.number_plate" placeholder="请输入本场参赛号码牌" maxlength="50" /></el-form-item></el-form><div class="section-actions"><el-button class="primary-button" :loading="busy" @click="createSupplement">补录并进入成绩登记</el-button></div></section>
        </template>

        <template v-if="section === 'score'">
          <section class="page-intro"><div><h2>登记挑战成绩</h2><p>查询参赛者后，填写现场确认的有效道具数量。</p></div></section>
          <section class="panel"><header><div><h3>查找参赛者</h3><p>支持姓名、手机号或号码牌</p></div></header><div class="section-actions"><el-input v-model="keyword" clearable placeholder="姓名、手机号或号码牌" @keyup.enter="searchRegistrations"><template #prefix><el-icon><Search /></el-icon></template></el-input><el-button class="primary-button" @click="searchRegistrations">查询</el-button></div><el-table :data="registrations" @row-click="selectRegistration"><el-table-column prop="number_plate" label="号码牌" width="130" /><el-table-column prop="name" label="姓名" /><el-table-column prop="phone" label="手机号" /><el-table-column prop="score" label="当前分数" /><el-table-column prop="status" label="状态" /><el-table-column label="操作" width="100"><template #default="scope"><el-button text class="table-action" @click.stop="selectRegistration(scope.row)">录分</el-button></template></el-table-column></el-table></section>
          <section v-if="selectedRegistration && config" class="panel score-panel"><header><div><h3>正在录入：{{ selectedRegistration.name }}（{{ selectedRegistration.number_plate }}）</h3><p>系统会根据有效数量自动计算总分。</p></div></header><el-alert title="只填写现场确认已完全装入且挑战结束未掉落的数量。" type="warning" :closable="false" show-icon /><el-table :data="config.score_items"><el-table-column prop="name" label="道具" /><el-table-column label="分值"><template #default="scope">{{ scope.row.points }} 分/个</template></el-table-column><el-table-column label="上限"><template #default="scope">{{ scope.row.max_quantity ?? '不限' }}</template></el-table-column><el-table-column label="有效数量" width="180"><template #default="scope"><el-input-number v-model="scoreForm[scope.row.id]" :min="0" :max="scope.row.max_quantity ?? 100" /></template></el-table-column></el-table><div class="save-score"><strong>预计总分：<b>{{ scorePreview }}</b> 分</strong><el-button class="primary-button" :loading="busy" @click="saveScore">保存成绩</el-button></div></section>
        </template>

        <template v-if="section === 'ranking'">
          <section class="page-intro"><div><h2>排行榜与最终抽奖</h2><p>分数相同的参赛者并列排名；最终抽奖结果只会保存一次。</p></div></section>
          <section class="two-column"><article class="panel"><header><div><h3>全场排行榜</h3><p>按已登记的总分排序</p></div></header><el-table :data="leaderboard?.entries || []"><el-table-column prop="rank" label="排名" width="80" /><el-table-column prop="number_plate" label="号码牌" /><el-table-column prop="display_name" label="展示名称" /><el-table-column prop="score" label="分数" /><el-table-column prop="title" label="奖励等级" /></el-table></article><aside class="panel draw-panel"><header><div><h3>最终抽奖</h3><p>赛事结束后由工作人员执行</p></div></header><p>达到 <b>{{ drawCandidates?.threshold ?? config?.draw_threshold }}</b> 分的参赛者可参与抽奖。</p><strong class="candidate-number">{{ drawCandidates?.items.length ?? 0 }}<small>人符合资格</small></strong><el-button class="primary-button" :disabled="(drawCandidates?.items.length ?? 0) < 2" @click="runDraw">随机抽取两位获奖者</el-button><el-alert v-if="drawResult" class="draw-alert" type="success" :closable="false" :title="drawResult.already_drawn ? '本活动已执行过抽奖' : '抽奖结果已保存'" /><ul v-if="drawResult" class="winner-list"><li v-for="winner in drawResult.results" :key="winner.prize_rank">第{{ winner.prize_rank }}名奖：报名编号 #{{ winner.registration_id }} · {{ winner.prize_name }}</li></ul><p class="hint">群内通知获奖者，结果保存后不可重复抽取。</p></aside></section>
        </template>

        <template v-if="section === 'settings' && config">
          <section class="page-intro"><div><h2>活动设置</h2><p>以下内容保存后立即在用户端和管理端生效。</p></div></section>
          <section class="panel"><header><div><h3>活动基本规则</h3><p>活动名称、状态和通用规则</p></div></header><el-form class="settings-form" label-position="top"><el-form-item label="活动名称"><el-input v-model="config.title" /></el-form-item><el-form-item label="活动状态"><el-select v-model="config.status"><el-option value="draft" label="草稿" /><el-option value="active" label="进行中" /><el-option value="ended" label="已结束" /></el-select></el-form-item><el-form-item label="挑战秒数"><el-input-number v-model="config.challenge_duration_seconds" :min="1" /></el-form-item><el-form-item label="每人挑战次数"><el-input-number v-model="config.challenge_limit" :min="1" /></el-form-item><el-form-item label="最终抽奖门槛"><el-input-number v-model="config.draw_threshold" :min="0" /></el-form-item><el-form-item class="full-span" label="规则文案"><el-input v-model="config.rules_text" type="textarea" :rows="4" /></el-form-item></el-form><el-button class="primary-button" @click="saveActivity">保存基本规则</el-button></section>
          <section class="panel"><header><div><h3>奖励区间</h3><p>分数区间必须从 0 分连续覆盖到最高分</p></div></header><el-table :data="config.reward_tiers"><el-table-column label="最低分"><template #default="scope"><el-input-number v-model="scope.row.min_score" :min="0" /></template></el-table-column><el-table-column label="最高分"><template #default="scope"><el-input-number v-model="scope.row.max_score" :min="0" placeholder="留空代表及以上" /></template></el-table-column><el-table-column label="等级"><template #default="scope"><el-input v-model="scope.row.title" /></template></el-table-column><el-table-column label="奖品"><template #default="scope"><el-input v-model="scope.row.prize_name" /></template></el-table-column></el-table><div class="section-actions spaced"><el-button class="secondary-button" @click="addTier">新增区间</el-button><el-button class="primary-button" @click="saveTiers">保存奖励区间</el-button></div></section>
          <section class="panel"><header><div><h3>计分道具</h3><p>每一行保存后会立即同步到成绩计算</p></div></header><el-table :data="config.score_items"><el-table-column prop="code" label="编码" width="145" /><el-table-column label="名称"><template #default="scope"><el-input v-model="scope.row.name" /></template></el-table-column><el-table-column label="分值" width="140"><template #default="scope"><el-input-number v-model="scope.row.points" :min="0" /></template></el-table-column><el-table-column label="上限" width="140"><template #default="scope"><el-input-number v-model="scope.row.max_quantity" :min="0" /></template></el-table-column><el-table-column label="操作" width="100"><template #default="scope"><el-button text class="table-action" @click="saveItem(scope.row)">保存</el-button></template></el-table-column></el-table></section>
          <section class="panel media-panel"><header><div><h3>移动端素材槽位</h3><p>素材保存在当前 ECS；新版视频和规则图上传后无需重新发布 H5。</p></div></header>
            <el-alert title="视频与竖版规则图统一要求 1080×1920；视频必须为 MP4/H.264。旧素材会保留，但新版移动端只读取以下固定槽位。" type="info" :closable="false" show-icon />
            <div class="media-slot-grid">
              <article v-for="slot in mediaSlots" :key="slot.kind" class="media-slot-card">
                <div class="media-slot-heading"><div><strong>{{ slot.label }}</strong><small>{{ slot.help }}</small></div><el-tag :type="slot.url ? 'success' : 'info'">{{ slot.url ? '已配置' : '待上传' }}</el-tag></div>
                <div v-if="slot.type !== 'link'" class="media-preview">
                  <video v-if="slot.type === 'video' && slot.url" :src="mediaPreviewUrl(slot.url)" controls preload="metadata" />
                  <img v-else-if="slot.type === 'image' && slot.url" :src="mediaPreviewUrl(slot.url)" :alt="slot.label" />
                  <span v-else>暂无素材</span>
                </div>
                <template v-if="slot.type === 'link'">
                  <el-input v-model="slot.url" placeholder="https:// 开头的抖音官方分享链接" />
                  <el-button class="primary-button" :loading="uploadingKind === slot.kind" @click="saveMedia(slot)">保存链接</el-button>
                </template>
                <el-upload v-else :show-file-list="false" :auto-upload="false" :accept="slot.accept" @change="uploadMedia(slot, $event.raw)">
                  <el-button class="primary-button" :loading="uploadingKind === slot.kind">{{ slot.url ? '替换素材' : '上传素材' }}</el-button>
                </el-upload>
              </article>
            </div>
          </section>
        </template>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Bell, EditPen, Odometer, Search, Setting, Trophy, UserFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, type Activity, type Dashboard, type DrawResult, type Leaderboard, type MediaAsset, type Registration, type ScoreItem } from './services/api'

type MediaSlot = MediaAsset & { type: 'video' | 'image' | 'link'; accept?: string; help: string }

const mediaSlotDefinitions: Array<Omit<MediaSlot, 'url' | 'object_key' | 'mime_type'>> = [
  { kind: 'demo_video_portrait', label: '竖版挑战示范视频', type: 'video', accept: 'video/mp4', help: '1080×1920 · MP4/H.264 · 30fps' },
  { kind: 'demo_video_poster_portrait', label: '竖版视频封面', type: 'image', accept: 'image/png,image/webp', help: '1080×1920 · PNG/WebP' },
  { kind: 'challenge_rule_portrait', label: '竖版挑战规则图', type: 'image', accept: 'image/png,image/webp', help: '1080×1920 · PNG/WebP' },
  { kind: 'score_reward_portrait', label: '竖版计分与奖励图', type: 'image', accept: 'image/png,image/webp', help: '1080×1920 · PNG/WebP' },
  { kind: 'douyin_qr', label: '抖音平台码', type: 'image', accept: 'image/png,image/webp,image/jpeg', help: '用于无法直接打开抖音时扫码' },
  { kind: 'taobao_qr', label: '淘宝店铺码', type: 'image', accept: 'image/png,image/webp,image/jpeg', help: '用于进入品牌淘宝店铺' },
  { kind: 'douyin_open_link', label: '抖音官方分享链接', type: 'link', help: '备用配置；当前第一页仅展示抖音二维码' },
]

const busy = ref(false), section = ref('dashboard'), dashboard = ref<Dashboard>(), config = ref<Activity>(), registrations = ref<Registration[]>([]), leaderboard = ref<Leaderboard>(), drawCandidates = ref<{ threshold: number; items: Array<{ registration_id: number; display_name: string; number_plate: string; score: number }> }>(), drawResult = ref<DrawResult>(), selectedRegistration = ref<Registration>(), keyword = ref(''), globalSearch = ref('')
const mediaSlots = ref<MediaSlot[]>([]), uploadingKind = ref('')
const scoreForm = reactive<Record<number, number>>({})
const supplementForm = reactive({ name: '', phone: '', number_plate: '' })
const heading = computed(() => ({ dashboard: '现场概况', supplement: '补录报名', score: '登记挑战成绩', ranking: '排行榜与抽奖', settings: '活动设置' }[section.value]))
const stats = computed(() => dashboard.value ? [
  { label: '报名人数', value: dashboard.value.registered_count, hint: '当前已完成报名', tone: 'neutral', icon: UserFilled },
  { label: '已录分', value: dashboard.value.scored_count, hint: '可在用户端查看', tone: 'positive', icon: EditPen },
  { label: '等待录分', value: dashboard.value.pending_score_count, hint: '需要现场处理', tone: 'warning', icon: Bell },
  { label: `${config.value?.draw_threshold ?? 45}分以上`, value: dashboard.value.draw_qualified_count, hint: '具备最终抽奖资格', tone: 'positive', icon: Trophy },
] : [])
const scoredRate = computed(() => !dashboard.value?.registered_count ? 0 : Math.round(dashboard.value.scored_count / dashboard.value.registered_count * 100))
const dashboardBars = computed(() => dashboard.value ? [
  { label: '报名完成度', value: dashboard.value.registered_count, suffix: ' 人', percentage: 100, color: '#6366f1' },
  { label: '成绩登记率', value: scoredRate.value, suffix: '%', percentage: scoredRate.value, color: '#10b981' },
  { label: '抽奖资格人数', value: dashboard.value.draw_qualified_count, suffix: ' 人', percentage: dashboard.value.scored_count ? Math.round(dashboard.value.draw_qualified_count / dashboard.value.scored_count * 100) : 0, color: '#f59e0b' },
] : [])
const scorePreview = computed(() => config.value?.score_items.reduce((sum, item) => sum + item.points * (scoreForm[item.id] || 0), 0) ?? 0)

function syncMediaSlots(assets: MediaAsset[]) { mediaSlots.value = mediaSlotDefinitions.map((definition) => ({ ...definition, ...(assets.find((asset) => asset.kind === definition.kind) || { url: '' }) })) }
async function loadAll() { try { const [dash, loadedConfig, ranks, candidates] = await Promise.all([adminApi.dashboard(), adminApi.config(), adminApi.leaderboard(), adminApi.drawCandidates()]); dashboard.value = dash; config.value = loadedConfig; syncMediaSlots(loadedConfig.media_assets); leaderboard.value = ranks; drawCandidates.value = candidates } catch (err) { ElMessage.error(err instanceof Error ? err.message : '数据加载失败') } }
async function changeSection(value: string) { section.value = value; if (value === 'score') await searchRegistrations(); if (value === 'ranking') await loadAll() }
async function searchFromTop() { keyword.value = globalSearch.value; await changeSection('score') }
async function searchRegistrations() { try { registrations.value = (await adminApi.registrations(keyword.value)).items } catch (err) { ElMessage.error(err instanceof Error ? err.message : '查询失败') } }
function selectRegistration(row: Registration) { selectedRegistration.value = row; for (const key of Object.keys(scoreForm)) delete scoreForm[Number(key)]; for (const item of config.value?.score_items || []) scoreForm[item.id] = 0 }
async function createSupplement() { if (!supplementForm.name.trim() || !/^\d{11}$/.test(supplementForm.phone) || !supplementForm.number_plate.trim()) { ElMessage.warning('请填写姓名、11位手机号和本场参赛号码牌'); return }; busy.value = true; try { const created = await adminApi.createRegistration(supplementForm); ElMessage.success('参赛者已补录，可直接登记成绩'); Object.assign(supplementForm, { name: '', phone: '', number_plate: '' }); selectRegistration(created); section.value = 'score'; await searchRegistrations() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '补录失败') } finally { busy.value = false } }
async function saveScore() { if (!selectedRegistration.value || !config.value) return; busy.value = true; try { const result = await adminApi.saveScore(selectedRegistration.value.id, config.value.score_items.map((item) => ({ score_item_id: item.id, quantity: scoreForm[item.id] || 0 }))); ElMessage.success(`成绩已保存：${(result as { total_score: number }).total_score} 分`); await loadAll(); await searchRegistrations() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '保存失败') } finally { busy.value = false } }
async function runDraw() { try { await ElMessageBox.confirm('将从符合资格的参赛者中随机抽取两位，结果会保存且不能重复抽取。确定执行吗？', '执行最终抽奖', { type: 'warning' }); drawResult.value = await adminApi.draw(); ElMessage.success('抽奖已执行并保存') } catch (err) { if (err !== 'cancel') ElMessage.error(err instanceof Error ? err.message : '抽奖失败') } }
async function saveActivity() { if (!config.value) return; try { config.value = await adminApi.updateActivity(config.value); ElMessage.success('活动规则已保存'); await loadAll() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '保存失败') } }
function addTier() { config.value?.reward_tiers.push({ min_score: 0, max_score: null, title: '新等级', prize_name: '待设置奖品', display_order: (config.value?.reward_tiers.length || 0) + 1 }) }
async function saveTiers() { if (!config.value) return; try { config.value = await adminApi.updateTiers(config.value.reward_tiers); ElMessage.success('奖励区间已保存') } catch (err) { ElMessage.error(err instanceof Error ? err.message : '请检查奖励区间是否连续') } }
async function saveItem(item: ScoreItem) { try { await adminApi.updateItem(item.id, item); ElMessage.success(`${item.name} 已保存`); await loadAll() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '保存失败') } }
function mediaPreviewUrl(url: string) { return url.startsWith('http') ? url : `/flipbelt-api${url}` }
async function saveMedia(media: MediaSlot) { if (media.type === 'link' && (!media.url || !/^https:\/\//i.test(media.url))) { ElMessage.warning('请输入 https:// 开头的官方分享链接'); return }; uploadingKind.value = media.kind; try { await adminApi.updateMedia(media); ElMessage.success('素材配置已保存'); await loadAll() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '保存失败') } finally { uploadingKind.value = '' } }
function imageDimensions(file: File) { return new Promise<{ width: number; height: number }>((resolve, reject) => { const url = URL.createObjectURL(file); const image = new Image(); image.onload = () => { URL.revokeObjectURL(url); resolve({ width: image.naturalWidth, height: image.naturalHeight }) }; image.onerror = () => { URL.revokeObjectURL(url); reject(new Error('无法读取图片尺寸')) }; image.src = url }) }
function videoDimensions(file: File) { return new Promise<{ width: number; height: number }>((resolve, reject) => { const url = URL.createObjectURL(file); const video = document.createElement('video'); video.preload = 'metadata'; video.onloadedmetadata = () => { URL.revokeObjectURL(url); resolve({ width: video.videoWidth, height: video.videoHeight }) }; video.onerror = () => { URL.revokeObjectURL(url); reject(new Error('无法读取视频信息，请确认文件为 MP4/H.264')) }; video.src = url }) }
async function validateMediaFile(media: MediaSlot, file: File) { if (media.type === 'video') { if (file.type !== 'video/mp4' && !file.name.toLowerCase().endsWith('.mp4')) throw new Error('视频必须为 MP4/H.264'); const size = await videoDimensions(file); if (size.width !== 1080 || size.height !== 1920) throw new Error(`视频尺寸为 ${size.width}×${size.height}，要求 1080×1920`) } else if (!['douyin_qr', 'taobao_qr'].includes(media.kind)) { if (!['image/png', 'image/webp'].includes(file.type)) throw new Error('竖版图片必须为 PNG 或 WebP'); const size = await imageDimensions(file); if (size.width !== 1080 || size.height !== 1920) throw new Error(`图片尺寸为 ${size.width}×${size.height}，要求 1080×1920`) } }
async function uploadMedia(media: MediaSlot, file?: File) { if (!file) return; uploadingKind.value = media.kind; try { await validateMediaFile(media, file); const uploaded = await adminApi.uploadMedia(media, file); Object.assign(media, uploaded); ElMessage.success('素材已保存到当前服务器并同步到前台'); await loadAll() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '上传失败') } finally { uploadingKind.value = '' } }
onMounted(() => { void loadAll() })
</script>
