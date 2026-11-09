<template>
  <main v-if="!authenticated" class="login-shell">
    <section class="login-card">
      <img class="login-wordmark" :src="brandLogo" alt="FLIPBELT" />
      <p class="eyebrow">40秒能装挑战 · 工作人员入口</p>
      <h1>登录现场管理台</h1>
      <p class="login-intro">请使用分配给你的工作人员账号。</p>
      <el-form label-position="top" @submit.prevent="login">
        <el-form-item label="账号"><el-input v-model="loginForm.username" autocomplete="username" :disabled="loggingIn" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password autocomplete="current-password" :disabled="loggingIn" /></el-form-item>
        <p v-if="loginError" class="login-error" role="alert">{{ loginError }}</p>
        <el-button class="primary-button login-button" native-type="submit" :loading="loggingIn">登录</el-button>
      </el-form>
    </section>
  </main>
  <el-container v-else class="admin-layout">
    <el-aside class="sidebar" width="256px">
      <div class="admin-logo"><div><img class="admin-wordmark" :src="brandLogo" alt="FLIPBELT" /><small>40秒能装挑战 · 管理台</small></div></div>
      <nav aria-label="后台导航">
        <el-menu :default-active="section" @select="changeSection">
          <el-menu-item index="dashboard"><el-icon><Odometer /></el-icon><span>现场概况</span></el-menu-item>
          <el-menu-item v-if="isAdmin" index="supplement"><el-icon><UserFilled /></el-icon><span>补录报名</span></el-menu-item>
          <el-menu-item index="score"><el-icon><EditPen /></el-icon><span>登记成绩</span></el-menu-item>
          <el-menu-item index="ranking"><el-icon><Trophy /></el-icon><span>排行榜与抽奖</span></el-menu-item>
          <el-menu-item v-if="isAdmin" index="settings"><el-icon><Setting /></el-icon><span>活动设置</span></el-menu-item>
        </el-menu>
      </nav>
      <div class="sidebar-footer"><span class="status-dot"></span>已连接现场管理台</div>
    </el-aside>
    <el-container class="main-area">
      <el-header class="topbar">
        <div><p class="eyebrow">活动运营</p><h1 ref="pageHeading" tabindex="-1">{{ heading }}</h1></div>
        <div class="topbar-actions">
          <el-input v-model="globalSearch" class="top-search" placeholder="搜索姓名、手机或号码牌" clearable @keyup.enter="searchFromTop"><template #prefix><el-icon><Search /></el-icon></template></el-input>
          <el-button class="icon-button" circle aria-label="通知"><el-icon><Bell /></el-icon></el-button>
          <div class="user-chip"><el-icon><UserFilled /></el-icon><span>{{ currentAdmin?.display_name || currentAdmin?.username }}</span></div>
          <el-button class="logout-button" @click="requestLogout">退出登录</el-button>
        </div>
        <button v-if="isMobile" ref="menuButton" type="button" class="mobile-link mobile-menu-trigger" aria-haspopup="dialog"
          :aria-expanded="menuOpen" @click="openMenu"><el-icon><Menu /></el-icon> 菜单</button>
      </el-header>
      <el-drawer v-if="isMobile" v-model="menuOpen" class="mobile-menu" title="现场管理台" direction="btt" size="auto"
        append-to-body :lock-scroll="false" @closed="restoreMenuFocus">
        <nav aria-label="手机后台导航">
          <button v-for="entry in mobileNavigation" :key="entry.id" type="button" class="mobile-list-row"
            :aria-current="section === entry.id ? 'page' : undefined" @click="chooseMobileSection(entry.id)">
            <span>{{ entry.label }}</span><span aria-hidden="true">{{ section === entry.id ? '当前' : '›' }}</span>
          </button>
          <button type="button" class="mobile-list-row mobile-danger" @click="menuOpen = false; requestLogout()">退出登录</button>
        </nav>
      </el-drawer>
      <el-main class="content">
        <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon /><el-button v-if="loadError" class="retry-button" :loading="loadingData" @click="loadAll">重新加载数据</el-button>
        <p v-if="loadingData && (!isMobile || !config)" role="status">正在加载活动数据…</p>
        <section v-if="isMobile && section === 'dashboard'" class="mobile-overview">
          <h2>活动概览</h2><p class="mobile-caption">{{ config?.title || '40秒能装挑战' }}</p>
          <div v-if="dashboard" class="mobile-stat-strip">
            <div><strong>{{ dashboard.registered_count }}</strong><small>已报名</small></div>
            <div><strong>{{ dashboard.pending_score_count }}</strong><small>待录分</small></div>
            <div><strong>{{ dashboard.scored_count }}</strong><small>已录分</small></div>
          </div>
          <p v-if="dashboardError" class="mobile-status" role="status">{{ dashboardError }}<button type="button" class="mobile-link" @click="loadDashboard">重试统计</button></p>
          <p v-if="dashboardUpdated" class="mobile-caption">统计更新于 {{ dashboardUpdated }}</p>
          <button type="button" class="mobile-primary" @click="changeSection('score')">开始录分</button>
          <button v-if="isAdmin" type="button" class="mobile-link" @click="changeSection('supplement')">补录报名 ›</button>
        </section>
        <template v-if="!isMobile && section === 'dashboard' && dashboard">
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

        <form v-if="isMobile && section === 'supplement' && isAdmin" class="mobile-fields" @submit.prevent="createSupplement">
          <p class="mobile-caption">补录成功后直接登记成绩。未提交的资料仅留在本页，刷新后需重新填写。</p>
          <label>号码牌<input v-model.trim="supplementForm.number_plate" maxlength="50" required enterkeyhint="next" :disabled="busy" /></label>
          <label>姓名<input v-model.trim="supplementForm.name" maxlength="80" required enterkeyhint="next" :disabled="busy" /></label>
          <label>手机号<input v-model.trim="supplementForm.phone" inputmode="numeric" maxlength="11" pattern="[0-9]{11}" required :disabled="busy" /></label>
          <div v-if="supplementError" class="mobile-status" role="alert">{{ supplementError }}
            <button v-if="supplementConflict" type="button" class="mobile-link" @click="findExistingSupplement">查现有报名 ›</button>
          </div>
          <div class="mobile-form-footer"><button class="mobile-primary" :disabled="busy">{{ busy ? '正在保存…' : '保存并去录分' }}</button></div>
        </form>
        <template v-if="!isMobile && section === 'supplement'">
          <section class="page-intro"><div><h2>补录报名</h2><p>用于现场网络异常或资料未成功保存时，补齐参赛者资料后直接录入成绩。</p></div></section>
          <section class="panel supplement-panel"><header><div><h3>补录参赛者</h3><p>手机号和号码牌不能与本场已有记录重复。</p></div></header><el-alert title="补录后会进入正常参赛名单，和用户扫码报名的数据完全一致。" type="info" :closable="false" show-icon /><el-form class="settings-form supplement-form" label-position="top" @submit.prevent="createSupplement"><el-form-item label="姓名"><el-input v-model="supplementForm.name" placeholder="请输入姓名" maxlength="80" /></el-form-item><el-form-item label="手机号"><el-input v-model="supplementForm.phone" placeholder="请输入11位手机号" maxlength="11" /></el-form-item><el-form-item label="参赛号码牌"><el-input v-model="supplementForm.number_plate" placeholder="请输入本场参赛号码牌" maxlength="50" /></el-form-item></el-form><div class="section-actions"><el-button class="primary-button" :loading="busy" @click="createSupplement">补录并进入成绩登记</el-button></div></section>
        </template>

        <MobileScore v-if="isMobile && section === 'score' && config && currentAdmin" :key="`${currentAdmin.id}:${config.id}`"
          ref="mobileScore" :config="config" :admin="currentAdmin" :refresh-rules="refreshConfig"
          @supplement="openSupplement" @changed="loadDashboard" />
        <template v-if="!isMobile && section === 'score'">
          <section class="page-intro"><div><h2>登记挑战成绩</h2><p>查询参赛者后，填写现场确认的有效道具数量。</p></div></section>
          <section class="panel"><header><div><h3>查找参赛者</h3><p>支持姓名、手机号或号码牌；修改成绩只会更新当前分数，删除成绩会保留报名资料。</p></div></header><div class="section-actions"><el-input v-model="keyword" clearable placeholder="姓名、手机号或号码牌" @keyup.enter="searchRegistrations"><template #prefix><el-icon><Search /></el-icon></template></el-input><el-button class="primary-button" @click="searchRegistrations">查询</el-button><el-button v-if="isAdmin" type="danger" plain :disabled="!registrations.some((row) => row.score != null)" @click="deleteAllScores">清空已录分</el-button></div><el-table :data="registrations" @row-click="selectRegistration"><el-table-column prop="number_plate" label="号码牌" width="130" /><el-table-column prop="name" label="姓名" /><el-table-column prop="phone" label="手机号" /><el-table-column prop="score" label="当前分数" /><el-table-column prop="status" label="状态" /><el-table-column label="操作" width="220"><template #default="scope"><el-button text class="table-action" @click.stop="selectRegistration(scope.row)">{{ scope.row.score == null ? '录分' : '修改分数' }}</el-button><el-button v-if="isAdmin && scope.row.score != null" text type="danger" @click.stop="deleteScore(scope.row)">删除分数</el-button></template></el-table-column></el-table></section>
          <section v-if="selectedRegistration && config" class="panel score-panel"><header><div><h3>{{ selectedRegistration.score == null ? '正在录入' : '正在修改' }}：{{ selectedRegistration.name }}（{{ selectedRegistration.number_plate }}）</h3><p>系统会根据有效数量自动计算总分。</p></div></header><el-alert :title="selectedRegistration.score == null ? '只填写现场确认已完全装入且挑战结束未掉落的数量。' : '修改后将覆盖该参赛者当前成绩，并同步用户端成绩与奖励。'" :type="selectedRegistration.score == null ? 'warning' : 'info'" :closable="false" show-icon /><el-table :data="config.score_items"><el-table-column prop="name" label="道具" /><el-table-column label="分值"><template #default="scope">{{ scope.row.points }} 分/个</template></el-table-column><el-table-column label="上限"><template #default="scope">{{ scope.row.max_quantity ?? '不限' }}</template></el-table-column><el-table-column label="有效数量" width="180"><template #default="scope"><el-input-number v-model="scoreForm[scope.row.id]" :min="0" :max="scope.row.max_quantity ?? 100" /></template></el-table-column></el-table><div class="save-score"><strong>预计总分：<b>{{ scorePreview }}</b> 分</strong><el-button class="primary-button" :loading="busy" @click="saveScore">{{ selectedRegistration.score == null ? '保存成绩' : '保存修改' }}</el-button></div></section>
        </template>

        <section v-if="isMobile && section === 'ranking'" class="mobile-rank">
          <button v-if="rankingView === 'list' && isAdmin" type="button" class="mobile-list-row" @click="openDraw">最终抽奖 <span aria-hidden="true">›</span></button>
          <template v-if="rankingView === 'list'">
            <h2>全场排行榜</h2>
            <p v-if="rankingError" class="mobile-status" role="status">{{ rankingError }}<button type="button" class="mobile-link" @click="loadLeaderboard()">重试</button></p>
            <p v-else-if="!leaderboard" role="status">正在加载排行榜…</p>
            <p v-else-if="!leaderboard.entries.length" class="mobile-caption">暂无已登记成绩</p>
            <ol v-else class="mobile-list">
              <li v-for="entry in leaderboard.entries" :key="entry.registration_id">
                <details class="mobile-rank-row">
                  <summary><span class="mobile-rank-place">{{ entry.rank }}</span><span><strong>#{{ entry.number_plate }}</strong><small>{{ entry.title || '—' }}</small></span><strong>{{ entry.score }} 分</strong></summary>
                  <p>{{ entry.name }} · {{ isAdmin ? entry.phone : `手机尾号 ${entry.phone.slice(-4)}` }}</p>
                </details>
              </li>
            </ol>
            <button v-if="leaderboard?.has_more" type="button" class="mobile-link" :disabled="loadingRanking" @click="loadLeaderboard(true)">查看更多排名</button>
          </template>
          <template v-else>
            <header class="mobile-section-head"><button type="button" class="mobile-link" @click="rankingView = 'list'">‹ 排行榜</button><h2>最终抽奖</h2></header>
            <p class="mobile-caption">资格线 {{ drawCandidates?.threshold ?? config?.draw_threshold ?? '—' }} 分 · {{ drawCandidates ? `${drawCandidates.items.length} 人符合资格` : '正在核对人数' }}</p>
            <p v-if="drawError" class="mobile-status" role="status">{{ drawError }}</p>
            <button v-if="drawError || drawUncertain" type="button" class="mobile-link" :disabled="drawBusy" @click="loadDraw">查询抽奖结果</button>
            <ul v-if="drawResult?.results.length" class="winner-list"><li v-for="winner in drawResult.results" :key="winner.prize_rank">第 {{ winner.prize_rank }} 名奖 · 报名编号 #{{ winner.registration_id }} · {{ winner.prize_name }}</li></ul>
            <button v-else type="button" class="mobile-primary" :disabled="drawBusy || drawUncertain || !drawResult || (drawCandidates?.items.length ?? 0) < 2" @click="runDraw">随机抽取两位获奖者</button>
            <p v-if="drawCandidates && drawCandidates.items.length < 2 && !drawResult?.results.length" class="mobile-caption">符合资格的选手不足两人。</p>
          </template>
        </section>
        <template v-if="!isMobile && section === 'ranking'">
          <section class="page-intro"><div><h2>排行榜与最终抽奖</h2><p>分数相同的参赛者并列排名；最终抽奖结果只会保存一次。</p></div></section>
          <section class="two-column"><article class="panel"><header><div><h3>全场排行榜</h3><p>按已登记的总分排序；后台显示现场登记姓名和手机号，便于和登记表核对</p></div></header><el-table :data="leaderboard?.entries || []"><el-table-column prop="rank" label="排名" width="80" /><el-table-column prop="number_plate" label="号码牌" /><el-table-column prop="name" label="现场姓名" /><el-table-column prop="phone" label="手机号" /><el-table-column prop="score" label="分数" /><el-table-column prop="title" label="奖励等级" /></el-table></article><aside class="panel draw-panel"><header><div><h3>最终抽奖</h3><p>赛事结束后由工作人员执行</p></div></header><p>达到 <b>{{ drawCandidates?.threshold ?? config?.draw_threshold }}</b> 分的参赛者可参与抽奖。</p><strong class="candidate-number">{{ drawCandidates?.items.length ?? 0 }}<small>人符合资格</small></strong><el-button v-if="isAdmin" class="primary-button" :disabled="(drawCandidates?.items.length ?? 0) < 2" @click="runDraw">随机抽取两位获奖者</el-button><el-alert v-if="drawResult" class="draw-alert" type="success" :closable="false" :title="drawResult.already_drawn ? '本活动已执行过抽奖' : '抽奖结果已保存'" /><ul v-if="drawResult" class="winner-list"><li v-for="winner in drawResult.results" :key="winner.prize_rank">第{{ winner.prize_rank }}名奖：报名编号 #{{ winner.registration_id }} · {{ winner.prize_name }}</li></ul><p class="hint">群内通知获奖者，结果保存后不可重复抽取。</p></aside></section>
        </template>

        <MobileSettings v-if="isMobile && section === 'settings' && config && isAdmin" :key="config.id"
          ref="mobileSettings" :config="config" @saved="applyConfig">
          <template #media>
            <p class="mobile-caption">视频、封面和规则图为 1080×1920；视频使用 MP4/H.264。</p>
            <details v-for="slot in mediaSlots" :key="slot.kind" class="mobile-media-slot" :open="openMediaKind === slot.kind"
              @toggle="toggleMedia(slot.kind, $event)">
              <summary><span>{{ slot.label }}</span><small>{{ slot.url ? '已配置' : '待配置' }}</small></summary>
              <div v-if="openMediaKind === slot.kind" class="mobile-fields mobile-inline-form">
                <p class="mobile-caption">{{ slot.help }}</p>
                <template v-if="slot.type === 'link'">
                  <label>抖音官方链接<input v-model="mediaLinkDraft" type="url" placeholder="https://" /></label>
                  <button type="button" class="mobile-primary" :disabled="Boolean(uploadingKind)" @click="saveMedia({ ...slot, url: mediaLinkDraft })">保存链接</button>
                </template>
                <template v-else>
                  <video v-if="slot.type === 'video' && slot.url" :src="mediaPreviewUrl(slot.url)" controls preload="metadata" />
                  <img v-else-if="slot.url" :src="mediaPreviewUrl(slot.url)" :alt="slot.label" />
                  <label>{{ slot.url ? '替换素材' : '选择素材' }}<input type="file" :accept="slot.accept" :disabled="Boolean(uploadingKind)" @change="uploadMobileMedia(slot, $event)" /></label>
                </template>
                <p v-if="uploadingKind === slot.kind" role="status">正在保存素材…</p>
                <p v-if="mediaStatus" role="status">{{ mediaStatus }}</p>
              </div>
            </details>
          </template>
          <template #danger>
            <p class="mobile-caption">清空本场已录成绩，保留报名资料。</p>
            <button type="button" class="mobile-link mobile-danger" :disabled="busy" @click="deleteAllScores">清空已录分</button>
          </template>
        </MobileSettings>
        <template v-if="!isMobile && section === 'settings' && config">
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
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { Bell, EditPen, Menu, Odometer, Search, Setting, Trophy, UserFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import brandLogo from '../../shared/branding/flipbelt.svg'
import MobileScore from './MobileScore.vue'
import MobileSettings from './MobileSettings.vue'
import { adminApi, ApiError, clearAdminToken, hasAdminToken, newOperationId, saveAdminToken, type Admin, type Activity, type Dashboard, type DrawResult, type Leaderboard, type MediaAsset, type Registration, type ScoreItem, type ScoreSubmission } from './services/api'
import { scoreDrafts } from './services/scoreDrafts'

const authenticated = ref(hasAdminToken())
const currentAdmin = ref<Admin>()
const isAdmin = computed(() => currentAdmin.value?.role === 'admin')
const loggingIn = ref(false)
const loginError = ref('')
const loadError = ref('')
const loadingData = ref(false)
const loginForm = reactive({ username: '', password: '' })
const mobileQuery = window.matchMedia('(max-width: 760px)')
const isMobile = ref(mobileQuery.matches), menuOpen = ref(false)
const menuButton = ref<HTMLButtonElement>(), pageHeading = ref<HTMLElement>()
const mobileScore = ref<InstanceType<typeof MobileScore>>(), mobileSettings = ref<InstanceType<typeof MobileSettings>>()
const dashboardError = ref(''), dashboardUpdated = ref(''), rankingError = ref('')
const rankingView = ref<'list' | 'draw'>('list'), loadingRanking = ref(false)
const drawError = ref(''), drawUncertain = ref(false), drawBusy = ref(false)
const supplementError = ref(''), supplementConflict = ref(false)
const openMediaKind = ref(''), mediaLinkDraft = ref(''), mediaStatus = ref('')
let sessionGeneration = 0
let menuSection = ''

function resetSession(message = '') {
  sessionGeneration += 1
  clearAdminToken()
  authenticated.value = false
  currentAdmin.value = undefined
  dashboard.value = undefined
  config.value = undefined
  registrations.value = []
  leaderboard.value = undefined
  selectedRegistration.value = undefined
  drawCandidates.value = undefined
  drawResult.value = undefined
  drawError.value = dashboardError.value = dashboardUpdated.value = rankingError.value = ''
  drawUncertain.value = false
  desktopAttempt = undefined
  keyword.value = globalSearch.value = ''
  mediaSlots.value = []
  openMediaKind.value = mediaLinkDraft.value = mediaStatus.value = ''
  menuOpen.value = false
  Object.assign(supplementForm, { name: '', phone: '', number_plate: '' })
  supplementError.value = ''
  loginForm.password = ''
  loginError.value = message
  loadError.value = ''
  section.value = 'dashboard'
}
function onUnauthorized() { resetSession('登录已过期，请重新登录') }
async function requestLogout() {
  if (!await canLeaveSection()) return
  const storage = config.value && currentAdmin.value ? scoreDrafts(currentAdmin.value.id, config.value.id) : undefined
  const count = storage?.list().length ?? 0
  if (count) {
    try { await ElMessageBox.confirm(`本机有 ${count} 条待处理记录，退出后将清除。`, '退出登录', { confirmButtonText: '清除并退出', cancelButtonText: '取消' }) }
    catch { return }
    storage?.clear()
  }
  resetSession()
}
function setAdmin(admin: Admin) {
  currentAdmin.value = admin
  if (isMobile.value && admin.role === 'scorer') section.value = 'score'
}
async function login() {
  if (loggingIn.value) return
  if (!loginForm.username.trim() || !loginForm.password) { loginError.value = '请填写账号和密码'; return }
  loggingIn.value = true
  loginError.value = ''
  try {
    const result = await adminApi.login(loginForm.username.trim(), loginForm.password)
    saveAdminToken(result.access_token)
    setAdmin(result.admin)
    loginForm.password = ''
    authenticated.value = true
    await loadAll()
  } catch (err) { loginError.value = err instanceof Error ? err.message : '登录失败，请重试' }
  finally { loggingIn.value = false }
}

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
let desktopAttempt: ScoreSubmission | undefined
const mobileNavigation = computed(() => [
  { id: 'dashboard', label: '现场概况' }, { id: 'score', label: '登记成绩' },
  { id: 'ranking', label: '排行榜' },
  ...(isAdmin.value ? [{ id: 'supplement', label: '补录报名' }, { id: 'settings', label: '活动设置' }] : []),
])
const heading = computed(() => ({ dashboard: '现场概况', supplement: '补录报名', score: '登记挑战成绩', ranking: '排行榜与抽奖', settings: '活动设置' }[section.value]))
const stats = computed(() => dashboard.value ? [
  { label: '报名人数', value: dashboard.value.registered_count, hint: '当前已完成报名', tone: 'neutral', icon: UserFilled },
  { label: '已录分', value: dashboard.value.scored_count, hint: '可在用户端查看', tone: 'positive', icon: EditPen },
  { label: '等待录分', value: dashboard.value.pending_score_count, hint: '需要现场处理', tone: 'warning', icon: Bell },
  { label: `${config.value?.draw_threshold ?? 45}分以上`, value: dashboard.value.draw_qualified_count, hint: '具备最终抽奖资格', tone: 'positive', icon: Trophy },
] : [])
const scoredRate = computed(() => !dashboard.value?.registered_count ? 0 : Math.round(dashboard.value.scored_count / dashboard.value.registered_count * 100))
const dashboardBars = computed(() => dashboard.value ? [
  { label: '报名完成度', value: dashboard.value.registered_count, suffix: ' 人', percentage: 100, color: '#526c2b' },
  { label: '成绩登记率', value: scoredRate.value, suffix: '%', percentage: scoredRate.value, color: '#10b981' },
  { label: '抽奖资格人数', value: dashboard.value.draw_qualified_count, suffix: ' 人', percentage: dashboard.value.scored_count ? Math.round(dashboard.value.draw_qualified_count / dashboard.value.scored_count * 100) : 0, color: '#f59e0b' },
] : [])
const scorePreview = computed(() => config.value?.score_items.reduce((sum, item) => sum + item.points * (scoreForm[item.id] || 0), 0) ?? 0)

function syncMediaSlots(assets: MediaAsset[]) { mediaSlots.value = mediaSlotDefinitions.map((definition) => ({ ...definition, ...(assets.find((asset) => asset.kind === definition.kind) || { url: '' }) })) }
function applyConfig(value: Activity) { config.value = value; syncMediaSlots(value.media_assets) }
async function refreshConfig() {
  const generation = sessionGeneration
  const value = await adminApi.config()
  if (generation === sessionGeneration) applyConfig(value)
  return value
}
async function loadDashboard() {
  const generation = sessionGeneration
  try {
    const value = await adminApi.dashboard()
    if (generation !== sessionGeneration) return
    dashboard.value = value
    dashboardError.value = ''
    dashboardUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch (error) { if (generation === sessionGeneration) dashboardError.value = error instanceof Error ? error.message : '统计读取失败' }
}
async function loadLeaderboard(more = false) {
  if (loadingRanking.value) return
  loadingRanking.value = true
  const generation = sessionGeneration
  rankingError.value = ''
  try {
    const previous = more ? leaderboard.value?.entries ?? [] : []
    const value = await adminApi.leaderboard(isMobile.value ? previous.length : undefined)
    if (generation === sessionGeneration) leaderboard.value = { ...value, entries: [...previous, ...value.entries] }
  }
  catch (error) { if (generation === sessionGeneration) rankingError.value = error instanceof Error ? error.message : '排行榜读取失败' }
  finally { loadingRanking.value = false }
}
async function loadDraw() {
  if (drawBusy.value) return
  const generation = sessionGeneration
  drawBusy.value = true
  drawError.value = ''
  try {
    const [candidates, result] = await Promise.all([adminApi.drawCandidates(), isAdmin.value ? adminApi.drawResult() : Promise.resolve(undefined)])
    if (generation !== sessionGeneration) return
    drawCandidates.value = candidates
    drawResult.value = result
    if (drawUncertain.value && !result?.results.length) drawError.value = '尚未查到抽奖结果，可再次查询或重新确认执行'
    drawUncertain.value = false
  } catch (error) { if (generation === sessionGeneration) drawError.value = error instanceof Error ? error.message : '抽奖信息读取失败' }
  finally { drawBusy.value = false }
}
async function openDraw() { rankingView.value = 'draw'; window.scrollTo(0, 0); await loadDraw() }
async function loadAll() {
  if (!authenticated.value) return
  const generation = sessionGeneration
  loadingData.value = true
  loadError.value = ''
  try {
    if (!currentAdmin.value) {
      const admin = await adminApi.me()
      if (generation !== sessionGeneration) return
      setAdmin(admin)
    }
    const tasks: Promise<unknown>[] = [refreshConfig(), loadDashboard()]
    if (!isMobile.value) tasks.push(loadLeaderboard(), loadDraw())
    await Promise.all(tasks)
  } catch (err) {
    if (generation === sessionGeneration) loadError.value = err instanceof Error ? err.message : '数据加载失败'
  } finally {
    if (generation === sessionGeneration) loadingData.value = false
  }
}
async function canLeaveSection() {
  if (busy.value || uploadingKind.value || drawBusy.value && rankingView.value === 'draw') return false
  if (mobileScore.value && !await mobileScore.value.canLeave()) return false
  if (mobileSettings.value && !await mobileSettings.value.canLeave()) return false
  if (isMobile.value && section.value === 'supplement' && Object.values(supplementForm).some(Boolean)) {
    try { await ElMessageBox.confirm('已填的报名资料暂留在本次登录页面内。', '离开补录', { confirmButtonText: '保留并离开', cancelButtonText: '继续填写' }) }
    catch { return false }
  }
  return true
}
async function changeSection(value: string) {
  if (value === section.value || !await canLeaveSection()) return
  if ((value === 'settings' || value === 'supplement') && !isAdmin.value) return
  section.value = value
  if (isMobile.value) window.scrollTo(0, 0)
  if (value === 'score' && !isMobile.value) await searchRegistrations()
  if (value === 'ranking') { rankingView.value = 'list'; await loadLeaderboard(); if (!isMobile.value) await loadDraw() }
  if (value === 'dashboard') void loadDashboard()
  if (value === 'settings') { openMediaKind.value = ''; mediaStatus.value = '' }
}
function openMenu() { menuSection = section.value; menuOpen.value = true }
function restoreMenuFocus() { (menuSection !== section.value ? pageHeading.value : menuButton.value)?.focus({ preventScroll: true }) }
function chooseMobileSection(value: string) { menuOpen.value = false; void changeSection(value) }
function updateViewport(event: MediaQueryListEvent) { isMobile.value = event.matches; menuOpen.value = false }
async function openSupplement(term: string) {
  await changeSection('supplement')
  if (section.value === 'supplement' && !supplementForm.number_plate && /^\d{1,10}$/.test(term)) supplementForm.number_plate = term
}
async function findExistingSupplement() {
  const term = supplementConflict.value && supplementError.value.startsWith('手机号') ? supplementForm.phone : supplementForm.number_plate
  await changeSection('score')
  if (section.value === 'score') await mobileScore.value?.find(term)
}
async function searchFromTop() { keyword.value = globalSearch.value; if (section.value === 'score') await searchRegistrations(); else await changeSection('score') }
async function searchRegistrations() { try { registrations.value = (await adminApi.registrations(keyword.value)).items } catch (err) { ElMessage.error(err instanceof Error ? err.message : '查询失败') } }
function selectRegistration(row: Registration) {
  desktopAttempt = undefined
  selectedRegistration.value = row
  for (const key of Object.keys(scoreForm)) delete scoreForm[Number(key)]
  for (const item of config.value?.score_items || []) scoreForm[item.id] = 0
  for (const detail of row.score_details || []) {
    if (detail.score_item_id in scoreForm) scoreForm[detail.score_item_id] = detail.quantity
  }
  void nextTick(() => document.querySelector<HTMLElement>('.score-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}
async function createSupplement() {
  if (busy.value || !isAdmin.value) return
  if (!supplementForm.name.trim() || !/^\d{11}$/.test(supplementForm.phone) || !supplementForm.number_plate.trim()) {
    supplementError.value = '请填写姓名、11位手机号和本场参赛号码牌'
    if (!isMobile.value) ElMessage.warning(supplementError.value)
    return
  }
  busy.value = true
  supplementError.value = ''
  supplementConflict.value = false
  const generation = sessionGeneration
  try {
    const created = await adminApi.createRegistration(supplementForm)
    if (generation !== sessionGeneration) return
    ElMessage.success('参赛者已补录，可直接登记成绩')
    Object.assign(supplementForm, { name: '', phone: '', number_plate: '' })
    section.value = 'score'
    if (isMobile.value) { await nextTick(); mobileScore.value?.edit(created) }
    else { selectRegistration(created); await searchRegistrations() }
    void loadDashboard()
  } catch (error) {
    if (generation !== sessionGeneration) return
    supplementError.value = error instanceof Error ? error.message : '补录失败'
    supplementConflict.value = error instanceof ApiError && error.status === 409
    if (!isMobile.value) ElMessage.error(supplementError.value)
  } finally { busy.value = false }
}
async function saveScore() {
  const row = selectedRegistration.value, activity = config.value
  if (!row || !activity || busy.value) return
  busy.value = true
  const items = activity.score_items.map((item) => ({ score_item_id: item.id, quantity: scoreForm[item.id] || 0 }))
  if (desktopAttempt && JSON.stringify(desktopAttempt.items) !== JSON.stringify(items)) {
    ElMessage.warning('上一笔保存结果待确认，请重新查找选手并核对后再修改')
    busy.value = false
    return
  }
  desktopAttempt ??= { activity_id: activity.id, registration_id: row.id, operation_id: newOperationId(),
    expected_version: row.score_version, rules_version: activity.rules_version, items }
  try {
    const result = await adminApi.submitScore(desktopAttempt)
    desktopAttempt = undefined
    ElMessage.success(`成绩已保存 · ${result.total_score} 分`)
    if (selectedRegistration.value?.id === row.id) selectedRegistration.value = { ...row, score: result.total_score, score_version: result.version, score_details: result.details }
    void loadDashboard()
    void searchRegistrations()
  } catch (error) {
    if (error instanceof ApiError && error.status && error.status < 500 && error.status !== 408) {
      desktopAttempt = undefined
      ElMessage.error(error.status === 409 ? `${error.message}，请重新查询并选中该选手` : error.message)
    } else ElMessage.warning('保存结果待确认，可用相同内容重试')
  } finally { busy.value = false }
}
async function deleteScore(row: Registration) {
  if (row.score == null) return
  try {
    await ElMessageBox.confirm(`确认删除 ${row.name}（${row.number_plate}）的 ${row.score} 分成绩吗？报名资料会保留，可重新录分。`, '删除成绩', { type: 'warning', confirmButtonText: '删除成绩', cancelButtonText: '取消' })
    busy.value = true
    await adminApi.deleteScore(row.id, row.score_version)
    if (selectedRegistration.value?.id === row.id) selectedRegistration.value = undefined
    ElMessage.success('成绩已删除，报名资料已保留')
    await loadAll()
    await searchRegistrations()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') ElMessage.error(err instanceof Error ? err.message : '删除失败')
  } finally {
    busy.value = false
  }
}
async function deleteAllScores() {
  if (!isAdmin.value || busy.value) return
  busy.value = true
  try {
    const current = await adminApi.dashboard()
    const scoredCount = current.scored_count
    if (!scoredCount) { ElMessage.info('本场暂无已录成绩'); return }
    await ElMessageBox.confirm(`确认清空当前活动全部 ${scoredCount} 条成绩吗？报名资料会保留，之后可以重新录分。`, '清空已录分', { type: 'warning', confirmButtonText: '清空成绩', cancelButtonText: '取消' })
    const result = await adminApi.deleteAllScores(current.activity.id, scoredCount)
    selectedRegistration.value = undefined
    ElMessage.success(`已删除 ${result.deleted_count} 条成绩`)
    await loadAll()
    await searchRegistrations()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') ElMessage.error(err instanceof Error ? err.message : '清空失败')
  } finally {
    busy.value = false
  }
}
async function runDraw() {
  const activityId = config.value?.id
  if (drawBusy.value || !isAdmin.value || !activityId) return
  drawBusy.value = true
  drawError.value = ''
  try {
    await ElMessageBox.confirm('将从符合资格的参赛者中随机抽取两位，结果会保存且不能重复抽取。确定执行吗？', '执行最终抽奖', { type: 'warning', confirmButtonText: '确认抽奖', cancelButtonText: '取消' })
    drawResult.value = await adminApi.draw(activityId)
    drawUncertain.value = false
    ElMessage.success('抽奖已执行并保存')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    drawUncertain.value = !(error instanceof ApiError) || !error.status || error.status >= 500 || error.status === 408
    drawError.value = drawUncertain.value ? '抽奖结果待确认，请先查询结果' : error instanceof Error ? error.message : '抽奖失败'
    if (!isMobile.value) ElMessage.warning(drawError.value)
  } finally { drawBusy.value = false }
}
async function saveActivity() { if (!config.value) return; try { applyConfig(await adminApi.updateActivity(config.value)); ElMessage.success('活动规则已保存'); await loadAll() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '保存失败') } }
function addTier() { config.value?.reward_tiers.push({ min_score: 0, max_score: null, title: '新等级', prize_name: '待设置奖品', display_order: (config.value?.reward_tiers.length || 0) + 1 }) }
async function saveTiers() { if (!config.value) return; try { applyConfig(await adminApi.updateTiers(config.value.reward_tiers)); ElMessage.success('奖励区间已保存') } catch (err) { ElMessage.error(err instanceof Error ? err.message : '请检查奖励区间是否连续') } }
async function saveItem(item: ScoreItem) { try { await adminApi.updateItem(item.id, item); ElMessage.success(`${item.name} 已保存`); await loadAll() } catch (err) { ElMessage.error(err instanceof Error ? err.message : '保存失败') } }
function mediaPreviewUrl(url: string) { return url.startsWith('http') ? url : `/flipbelt-api${url}` }
function toggleMedia(kind: string, event: Event) {
  if ((event.target as HTMLDetailsElement).open && openMediaKind.value !== kind) {
    openMediaKind.value = kind
    mediaLinkDraft.value = mediaSlots.value.find((slot) => slot.kind === kind)?.url ?? ''
    mediaStatus.value = ''
  } else if (!(event.target as HTMLDetailsElement).open && openMediaKind.value === kind) openMediaKind.value = ''
}
function showMediaStatus(text: string, success: boolean) {
  if (isMobile.value) mediaStatus.value = text
  else if (success) ElMessage.success(text)
  else ElMessage.error(text)
}
async function saveMedia(media: MediaSlot) {
  if (uploadingKind.value) return
  if (media.type === 'link' && (!media.url || !/^https:\/\//i.test(media.url))) { showMediaStatus('请输入 https:// 开头的官方分享链接', false); return }
  uploadingKind.value = media.kind
  mediaStatus.value = ''
  try { await adminApi.updateMedia(media); showMediaStatus('素材配置已保存', true); await refreshConfig() }
  catch (error) { showMediaStatus(error instanceof Error ? error.message : '保存失败', false) }
  finally { uploadingKind.value = '' }
}
function imageDimensions(file: File) { return new Promise<{ width: number; height: number }>((resolve, reject) => { const url = URL.createObjectURL(file); const image = new Image(); image.onload = () => { URL.revokeObjectURL(url); resolve({ width: image.naturalWidth, height: image.naturalHeight }) }; image.onerror = () => { URL.revokeObjectURL(url); reject(new Error('无法读取图片尺寸')) }; image.src = url }) }
function videoDimensions(file: File) { return new Promise<{ width: number; height: number }>((resolve, reject) => { const url = URL.createObjectURL(file); const video = document.createElement('video'); video.preload = 'metadata'; video.onloadedmetadata = () => { URL.revokeObjectURL(url); resolve({ width: video.videoWidth, height: video.videoHeight }) }; video.onerror = () => { URL.revokeObjectURL(url); reject(new Error('无法读取视频信息，请确认文件为 MP4/H.264')) }; video.src = url }) }
async function validateMediaFile(media: MediaSlot, file: File) { if (media.type === 'video') { if (file.type !== 'video/mp4' && !file.name.toLowerCase().endsWith('.mp4')) throw new Error('视频必须为 MP4/H.264'); const size = await videoDimensions(file); if (size.width !== 1080 || size.height !== 1920) throw new Error(`视频尺寸为 ${size.width}×${size.height}，要求 1080×1920`) } else if (!['douyin_qr', 'taobao_qr'].includes(media.kind)) { if (!['image/png', 'image/webp'].includes(file.type)) throw new Error('竖版图片必须为 PNG 或 WebP'); const size = await imageDimensions(file); if (size.width !== 1080 || size.height !== 1920) throw new Error(`图片尺寸为 ${size.width}×${size.height}，要求 1080×1920`) } }
async function uploadMedia(media: MediaSlot, file?: File) {
  if (!file || uploadingKind.value) return
  uploadingKind.value = media.kind
  mediaStatus.value = ''
  let sent = false
  try {
    await validateMediaFile(media, file)
    sent = true
    const uploaded = await adminApi.uploadMedia(media, file)
    Object.assign(media, uploaded)
    showMediaStatus('素材已保存', true)
  } catch (error) {
    const uncertain = sent && (!(error instanceof ApiError) || !error.status || error.status >= 500 || error.status === 408)
    if (!uncertain) showMediaStatus(error instanceof Error ? error.message : '上传失败', false)
    else {
      try {
        const current = (await refreshConfig()).media_assets.find((asset) => asset.kind === media.kind)
        showMediaStatus(current?.url !== media.url ? '服务器槽位已更新，请预览核对' : '未查到新素材，请核对后重试', false)
      } catch { showMediaStatus('上传结果待确认，请联网后重新打开槽位核对', false) }
    }
  } finally { uploadingKind.value = '' }
}
function uploadMobileMedia(media: MediaSlot, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  void uploadMedia(media, file)
}
onMounted(async () => {
  window.addEventListener('flipbelt-admin-unauthorized', onUnauthorized)
  mobileQuery.addEventListener('change', updateViewport)
  if (!authenticated.value) return
  try { await loadAll() }
  catch (err) {
    if (authenticated.value) loadError.value = err instanceof Error ? err.message : '数据加载失败'
  }
})
onUnmounted(() => { window.removeEventListener('flipbelt-admin-unauthorized', onUnauthorized); mobileQuery.removeEventListener('change', updateViewport) })
</script>
