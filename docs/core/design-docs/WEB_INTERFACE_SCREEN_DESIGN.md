# 바이낸스 스타일 웹 인터페이스 화면 설계서

## 📋 문서 개요

**문서 목적**: Letrade V1 웹 인터페이스의 상세한 화면 설계 및 UX/UI 가이드라인

**설계 철학**: 바이낸스 Pro 수준의 전문적이고 직관적인 거래 인터페이스

**대상 사용자**: 암호화폐 거래 경험이 있는 개인 투자자

## 🎨 디자인 시스템

### 컬러 팔레트 (바이낸스 스타일)
```css
:root {
  /* 메인 배경 */
  --bg-primary: #0b0e11;      /* 다크 네이비 */
  --bg-secondary: #1e2329;    /* 미드 그레이 */
  --bg-tertiary: #2b3139;     /* 라이트 그레이 */
  
  /* 텍스트 */
  --text-primary: #f0f0f0;    /* 화이트 */
  --text-secondary: #c7c7c7;  /* 라이트 그레이 */
  --text-muted: #888888;      /* 뮤트 그레이 */
  
  /* 액센트 */
  --accent-green: #0ecb81;    /* 상승/매수 */
  --accent-red: #f6465d;      /* 하락/매도 */
  --accent-yellow: #fcd535;   /* 경고/대기 */
  --accent-blue: #00d4ff;     /* 정보/링크 */
  
  /* 상태 */
  --success: #0ecb81;
  --warning: #fcd535;
  --danger: #f6465d;
  --info: #00d4ff;
  
  /* 보더 */
  --border-primary: #2b3139;
  --border-light: #404040;
  
  /* 그라데이션 */
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-success: linear-gradient(135deg, #0ecb81 0%, #00b894 100%);
  --gradient-danger: linear-gradient(135deg, #f6465d 0%, #e84393 100%);
}
```

### 타이포그래피
```css
/* 폰트 패밀리 */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* 폰트 크기 */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */

/* 폰트 가중치 */
--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 간격 시스템
```css
/* 스페이싱 */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */

/* 보더 반경 */
--radius-sm: 0.25rem;  /* 4px */
--radius-md: 0.5rem;   /* 8px */
--radius-lg: 0.75rem;  /* 12px */
--radius-xl: 1rem;     /* 16px */
```

## 📱 화면 구성

### 1. 메인 대시보드 (1920x1080 기준)

#### 1.1 전체 레이아웃
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  헤더 영역 (높이: 64px)                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 사이드바 │                        메인 컨텐츠 영역                               │
│(폭:240px)│                      (1680x976px)                                  │
│          │                                                                     │
│  네비     │  ┌─────────────┬─────────────┬─────────────┐                      │
│  메뉴     │  │   위젯 1    │   위젯 2    │   위젯 3    │                      │
│          │  │             │             │             │                      │
│  📊 대시보드│  │             │             │             │                      │
│  💰 거래   │  ├─────────────┼─────────────┼─────────────┤                      │
│  📈 차트   │  │   위젯 4    │   위젯 5    │   위젯 6    │                      │
│  🎯 전략   │  │             │             │             │                      │
│  📋 내역   │  │             │             │             │                      │
│  ⚙️ 설정   │  ├─────────────┼─────────────┼─────────────┤                      │
│  📱 텔레그램│  │   위젯 7    │   위젯 8    │   위젯 9    │                      │
│          │  │             │             │             │                      │
│          │  └─────────────┴─────────────┴─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 1.2 헤더 영역 상세 설계
```html
<header class="header">
  <div class="header-left">
    <!-- 로고 및 시스템 상태 -->
    <div class="logo">
      <span class="logo-icon">🚀</span>
      <span class="logo-text">LETRADE V1 PRO</span>
    </div>
    
    <!-- 실시간 상태 표시 -->
    <div class="status-indicators">
      <div class="status-item">
        <span class="status-dot animate-pulse bg-green-500"></span>
        <span class="status-text">실시간</span>
      </div>
      
      <div class="status-item">
        <span class="status-dot bg-green-500"></span>
        <span class="status-text">연결됨</span>
      </div>
      
      <div class="latency-indicator">
        <span class="latency-value">1.9ms</span>
      </div>
    </div>
  </div>
  
  <div class="header-center">
    <!-- 포트폴리오 요약 -->
    <div class="portfolio-summary">
      <div class="portfolio-item">
        <span class="label">총 자산:</span>
        <span class="value">$1,234.56</span>
        <span class="change positive">+2.34%</span>
      </div>
      
      <div class="portfolio-item">
        <span class="label">일일 P&L:</span>
        <span class="value">+$12.34</span>
        <span class="change positive">+1.02%</span>
      </div>
    </div>
  </div>
  
  <div class="header-right">
    <!-- 사용자 정보 및 설정 -->
    <div class="user-controls">
      <button class="notification-btn">
        <span class="icon">🔔</span>
        <span class="badge">3</span>
      </button>
      
      <div class="user-menu">
        <span class="user-avatar">👤</span>
        <span class="user-name">Admin</span>
        <span class="dropdown-icon">⌄</span>
      </div>
      
      <button class="settings-btn">⚙️</button>
    </div>
  </div>
</header>
```

#### 1.3 사이드바 네비게이션
```html
<aside class="sidebar">
  <nav class="nav-menu">
    <div class="nav-section">
      <div class="nav-title">모니터링</div>
      <a href="/dashboard" class="nav-item active">
        <span class="nav-icon">📊</span>
        <span class="nav-text">대시보드</span>
      </a>
      <a href="/portfolio" class="nav-item">
        <span class="nav-icon">💰</span>
        <span class="nav-text">포트폴리오</span>
      </a>
    </div>
    
    <div class="nav-section">
      <div class="nav-title">거래</div>
      <a href="/charts" class="nav-item">
        <span class="nav-icon">📈</span>
        <span class="nav-text">차트</span>
      </a>
      <a href="/strategies" class="nav-item">
        <span class="nav-icon">🎯</span>
        <span class="nav-text">전략</span>
        <span class="nav-badge">3</span>
      </a>
      <a href="/history" class="nav-item">
        <span class="nav-icon">📋</span>
        <span class="nav-text">거래내역</span>
      </a>
    </div>
    
    <div class="nav-section">
      <div class="nav-title">시스템</div>
      <a href="/settings" class="nav-item">
        <span class="nav-icon">⚙️</span>
        <span class="nav-text">설정</span>
      </a>
      <a href="/telegram" class="nav-item">
        <span class="nav-icon">📱</span>
        <span class="nav-text">텔레그램</span>
        <span class="nav-status online"></span>
      </a>
    </div>
  </nav>
  
  <!-- 시스템 상태 요약 -->
  <div class="sidebar-footer">
    <div class="system-status">
      <div class="status-row">
        <span>시스템:</span>
        <span class="status-value online">정상</span>
      </div>
      <div class="status-row">
        <span>전략:</span>
        <span class="status-value">1개 활성</span>
      </div>
    </div>
  </div>
</aside>
```

### 2. 위젯 상세 설계

#### 2.1 실시간 시장 현황 위젯
```html
<div class="widget market-overview">
  <div class="widget-header">
    <h3 class="widget-title">📊 실시간 시장 현황</h3>
    <div class="widget-controls">
      <button class="refresh-btn">🔄</button>
      <button class="settings-btn">⚙️</button>
    </div>
  </div>
  
  <div class="widget-content">
    <div class="market-grid">
      <!-- BTC -->
      <div class="market-item">
        <div class="symbol">
          <img src="/icons/btc.svg" class="coin-icon" />
          <span class="symbol-text">BTC/USDT</span>
        </div>
        <div class="price">
          <span class="price-value">$50,234.56</span>
          <span class="price-change positive">+1.23%</span>
        </div>
        <div class="volume">
          <span class="volume-label">24h 거래량:</span>
          <span class="volume-value">1,234 BTC</span>
        </div>
      </div>
      
      <!-- ETH -->
      <div class="market-item">
        <div class="symbol">
          <img src="/icons/eth.svg" class="coin-icon" />
          <span class="symbol-text">ETH/USDT</span>
        </div>
        <div class="price">
          <span class="price-value">$2,987.45</span>
          <span class="price-change negative">-0.45%</span>
        </div>
        <div class="volume">
          <span class="volume-label">24h 거래량:</span>
          <span class="volume-value">5,678 ETH</span>
        </div>
      </div>
      
      <!-- 추가 코인들... -->
    </div>
    
    <!-- 실시간 업데이트 표시 -->
    <div class="update-indicator">
      <span class="update-dot animate-pulse"></span>
      <span class="update-text">실시간 업데이트</span>
      <span class="update-time">14:35:22</span>
    </div>
  </div>
</div>
```

#### 2.2 포지션 관리 위젯
```html
<div class="widget position-manager">
  <div class="widget-header">
    <h3 class="widget-title">💰 포지션 관리</h3>
    <div class="position-summary">
      <span class="total-pnl positive">+$12.34</span>
    </div>
  </div>
  
  <div class="widget-content">
    <div class="positions-list">
      <!-- 활성 포지션 -->
      <div class="position-item">
        <div class="position-header">
          <div class="symbol-info">
            <span class="symbol">BTCUSDT</span>
            <span class="side long">Long</span>
          </div>
          <div class="position-actions">
            <button class="action-btn close-btn">🗙</button>
            <button class="action-btn settings-btn">⚙️</button>
          </div>
        </div>
        
        <div class="position-details">
          <div class="detail-row">
            <span class="label">크기:</span>
            <span class="value">0.001 BTC</span>
          </div>
          <div class="detail-row">
            <span class="label">진입가:</span>
            <span class="value">$50,000.00</span>
          </div>
          <div class="detail-row">
            <span class="label">현재가:</span>
            <span class="value">$50,234.56</span>
          </div>
          <div class="detail-row">
            <span class="label">P&L:</span>
            <span class="value positive">+$0.23 (+0.47%)</span>
          </div>
        </div>
        
        <!-- 포지션 차트 (미니) -->
        <div class="position-chart">
          <canvas id="position-chart-btc" width="200" height="60"></canvas>
        </div>
      </div>
      
      <!-- 포지션이 없는 경우 -->
      <div class="no-positions" style="display: none;">
        <div class="empty-state">
          <span class="empty-icon">📭</span>
          <span class="empty-text">활성 포지션이 없습니다</span>
          <button class="start-trading-btn">거래 시작</button>
        </div>
      </div>
    </div>
  </div>
</div>
```

#### 2.3 성과 차트 위젯
```html
<div class="widget performance-chart">
  <div class="widget-header">
    <h3 class="widget-title">📈 성과 차트</h3>
    <div class="chart-controls">
      <div class="timeframe-selector">
        <button class="timeframe-btn active">1D</button>
        <button class="timeframe-btn">1W</button>
        <button class="timeframe-btn">1M</button>
        <button class="timeframe-btn">3M</button>
      </div>
    </div>
  </div>
  
  <div class="widget-content">
    <!-- Chart.js 또는 D3.js 차트 -->
    <div class="chart-container">
      <canvas id="performance-chart" width="400" height="200"></canvas>
    </div>
    
    <!-- 차트 하단 메트릭 -->
    <div class="chart-metrics">
      <div class="metric-item">
        <span class="metric-label">총 수익률:</span>
        <span class="metric-value positive">+2.34%</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">최대 드로우다운:</span>
        <span class="metric-value negative">-1.23%</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">샤프 비율:</span>
        <span class="metric-value">1.42</span>
      </div>
    </div>
  </div>
</div>
```

#### 2.4 전략 제어 위젯
```html
<div class="widget strategy-control">
  <div class="widget-header">
    <h3 class="widget-title">⚡ 전략 제어</h3>
    <div class="system-status">
      <span class="status-indicator active"></span>
      <span class="status-text">시스템 활성</span>
    </div>
  </div>
  
  <div class="widget-content">
    <!-- 메인 제어 버튼 -->
    <div class="control-buttons">
      <button class="control-btn primary start-btn">
        <span class="btn-icon">▶️</span>
        <span class="btn-text">시작</span>
      </button>
      <button class="control-btn warning pause-btn">
        <span class="btn-icon">⏸️</span>
        <span class="btn-text">일시정지</span>
      </button>
      <button class="control-btn danger stop-btn">
        <span class="btn-icon">🛑</span>
        <span class="btn-text">중지</span>
      </button>
      <button class="control-btn secondary restart-btn">
        <span class="btn-icon">🔄</span>
        <span class="btn-text">재시작</span>
      </button>
    </div>
    
    <!-- 활성 전략 목록 -->
    <div class="active-strategies">
      <div class="strategy-item">
        <div class="strategy-info">
          <span class="strategy-name">MA Crossover</span>
          <span class="strategy-symbol">BTCUSDT</span>
        </div>
        <div class="strategy-status">
          <span class="status-indicator active"></span>
          <span class="status-text">활성</span>
        </div>
        <div class="strategy-performance">
          <span class="performance-value positive">+1.23%</span>
        </div>
        <div class="strategy-actions">
          <button class="action-btn">⏸️</button>
          <button class="action-btn">⚙️</button>
        </div>
      </div>
    </div>
    
    <!-- 빠른 액션 -->
    <div class="quick-actions">
      <button class="quick-action-btn">
        <span class="action-icon">🚨</span>
        <span class="action-text">긴급 중지</span>
      </button>
      <button class="quick-action-btn">
        <span class="action-icon">📊</span>
        <span class="action-text">상태 확인</span>
      </button>
    </div>
  </div>
</div>
```

#### 2.5 텔레그램 연동 위젯
```html
<div class="widget telegram-integration">
  <div class="widget-header">
    <h3 class="widget-title">📱 텔레그램 연동</h3>
    <div class="connection-status">
      <span class="status-dot online"></span>
      <span class="status-text">연결됨</span>
    </div>
  </div>
  
  <div class="widget-content">
    <!-- 최근 활동 -->
    <div class="recent-activity">
      <div class="activity-item">
        <div class="activity-time">14:35:22</div>
        <div class="activity-content">
          <span class="activity-type incoming">📥</span>
          <span class="activity-text">/status 명령 수신</span>
        </div>
      </div>
      
      <div class="activity-item">
        <div class="activity-time">14:32:18</div>
        <div class="activity-content">
          <span class="activity-type outgoing">📤</span>
          <span class="activity-text">거래 실행 알림 전송</span>
        </div>
      </div>
      
      <div class="activity-item">
        <div class="activity-time">14:30:15</div>
        <div class="activity-content">
          <span class="activity-type incoming">📥</span>
          <span class="activity-text">/portfolio 명령 수신</span>
        </div>
      </div>
    </div>
    
    <!-- 빠른 전송 -->
    <div class="quick-send">
      <div class="send-controls">
        <input type="text" class="message-input" placeholder="테스트 메시지 입력..." />
        <button class="send-btn">📤</button>
      </div>
      
      <div class="preset-messages">
        <button class="preset-btn">📊 상태 보고</button>
        <button class="preset-btn">💰 잔고 확인</button>
        <button class="preset-btn">🎯 전략 현황</button>
      </div>
    </div>
    
    <!-- 연동 설정 -->
    <div class="telegram-settings">
      <div class="setting-item">
        <span class="setting-label">자동 알림:</span>
        <label class="toggle">
          <input type="checkbox" checked />
          <span class="toggle-slider"></span>
        </label>
      </div>
      
      <div class="setting-item">
        <span class="setting-label">알림 레벨:</span>
        <select class="setting-select">
          <option value="all">모든 알림</option>
          <option value="important">중요 알림만</option>
          <option value="critical">긴급 알림만</option>
        </select>
      </div>
    </div>
  </div>
</div>
```

### 3. 반응형 설계

#### 3.1 브레이크포인트
```css
/* 브레이크포인트 정의 */
$breakpoints: (
  'xs': 0,
  'sm': 576px,
  'md': 768px,
  'lg': 992px,
  'xl': 1200px,
  'xxl': 1400px
);

/* 모바일 우선 미디어 쿼리 */
@media (max-width: 767px) {
  .sidebar {
    transform: translateX(-100%);
    position: fixed;
    z-index: 1000;
    transition: transform 0.3s ease;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .main-content {
    margin-left: 0;
  }
  
  .widget-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .header {
    padding: 0 1rem;
  }
  
  .header-center {
    display: none;
  }
}

@media (min-width: 768px) and (max-width: 991px) {
  .widget-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .sidebar {
    width: 200px;
  }
}

@media (min-width: 992px) {
  .widget-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

#### 3.2 모바일 네비게이션
```html
<!-- 모바일 헤더 -->
<header class="mobile-header">
  <button class="menu-toggle">☰</button>
  <div class="logo">🚀 LETRADE</div>
  <div class="mobile-summary">
    <span class="balance">$1,234</span>
    <span class="change positive">+2.3%</span>
  </div>
</header>

<!-- 모바일 사이드바 오버레이 -->
<div class="sidebar-overlay" onclick="closeSidebar()"></div>
```

### 4. 인터랙션 및 애니메이션

#### 4.1 CSS 애니메이션
```css
/* 로딩 애니메이션 */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes countUp {
  from { transform: scale(0.8); }
  to { transform: scale(1); }
}

/* 상태 표시 애니메이션 */
.status-dot.animate-pulse {
  animation: pulse 2s infinite;
}

.price-change.updated {
  animation: countUp 0.3s ease-out;
}

/* 호버 효과 */
.widget:hover {
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  transition: all 0.3s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transition: all 0.2s ease;
}
```

#### 4.2 JavaScript 인터랙션
```javascript
// 실시간 데이터 업데이트 애니메이션
function updatePrice(element, newPrice, oldPrice) {
  element.textContent = formatPrice(newPrice);
  
  // 가격 변화에 따른 색상 변경
  if (newPrice > oldPrice) {
    element.classList.add('price-up');
    setTimeout(() => element.classList.remove('price-up'), 500);
  } else if (newPrice < oldPrice) {
    element.classList.add('price-down');
    setTimeout(() => element.classList.remove('price-down'), 500);
  }
}

// 위젯 드래그 앤 드롭 (대시보드 커스터마이징)
function initializeDragAndDrop() {
  const widgets = document.querySelectorAll('.widget');
  
  widgets.forEach(widget => {
    widget.addEventListener('dragstart', handleDragStart);
    widget.addEventListener('dragover', handleDragOver);
    widget.addEventListener('drop', handleDrop);
  });
}

// 반응형 차트 리사이즈
function handleResize() {
  charts.forEach(chart => {
    chart.resize();
  });
}
```

### 5. 접근성 (Accessibility)

#### 5.1 WCAG 2.1 준수
```html
<!-- 시맨틱 HTML -->
<main role="main" aria-label="메인 대시보드">
  <section aria-labelledby="portfolio-section">
    <h2 id="portfolio-section">포트폴리오 현황</h2>
    <!-- 포트폴리오 내용 -->
  </section>
</main>

<!-- 키보드 네비게이션 -->
<button tabindex="0" aria-label="전략 시작" onclick="startStrategy()">
  ▶️ 시작
</button>

<!-- 스크린 리더 지원 -->
<div aria-live="polite" aria-atomic="true" id="price-announcer">
  <!-- 가격 변화 알림 -->
</div>
```

#### 5.2 키보드 단축키
```javascript
// 키보드 단축키 시스템
const shortcuts = {
  'Ctrl+S': () => saveCurrentLayout(),
  'Ctrl+R': () => refreshAllWidgets(),
  'Space': () => toggleSystemPause(),
  'Escape': () => closeActiveModal(),
  'F5': () => location.reload(),
  '1': () => navigateToSection('dashboard'),
  '2': () => navigateToSection('portfolio'),
  '3': () => navigateToSection('charts'),
  '4': () => navigateToSection('strategies')
};
```

### 6. 성능 최적화

#### 6.1 이미지 최적화
```html
<!-- 반응형 이미지 -->
<picture>
  <source media="(max-width: 768px)" srcset="chart-mobile.webp">
  <source media="(max-width: 1200px)" srcset="chart-tablet.webp">
  <img src="chart-desktop.webp" alt="성과 차트" loading="lazy">
</picture>

<!-- 아이콘 최적화 -->
<svg class="icon" width="24" height="24" viewBox="0 0 24 24">
  <use href="#icon-btc"></use>
</svg>
```

#### 6.2 CSS 최적화
```css
/* GPU 가속 활용 */
.animated-element {
  will-change: transform;
  transform: translateZ(0);
}

/* Critical CSS 인라인 */
<style>
  /* 첫 화면에 필요한 최소 CSS만 인라인 */
  .header { /* ... */ }
  .widget { /* ... */ }
</style>

/* 나머지 CSS는 비동기 로드 */
<link rel="preload" href="styles.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
```

## 📐 컴포넌트 라이브러리

### 기본 컴포넌트
```typescript
// Button 컴포넌트
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'success' | 'danger' | 'warning';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  onClick?: () => void;
  children: React.ReactNode;
}

// Card 컴포넌트
interface CardProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  loading?: boolean;
  error?: string;
  children: React.ReactNode;
}

// Table 컴포넌트
interface TableProps {
  columns: TableColumn[];
  data: any[];
  loading?: boolean;
  pagination?: boolean;
  sortable?: boolean;
  selectable?: boolean;
}
```

---

## 🎯 구현 우선순위

### Phase 1: 핵심 레이아웃 (1주차)
- ✅ 헤더 및 네비게이션
- ✅ 메인 대시보드 그리드
- ✅ 기본 위젯 구조
- ✅ 반응형 레이아웃

### Phase 2: 데이터 연동 (2주차)
- ✅ WebSocket 실시간 연결
- ✅ API 데이터 바인딩
- ✅ 차트 및 그래프
- ✅ 상태 관리

### Phase 3: 고급 기능 (3주차)
- ✅ 인터랙티브 제어
- ✅ 텔레그램 연동
- ✅ 커스터마이징
- ✅ 성능 최적화

---

*이 화면 설계서는 바이낸스 수준의 전문적인 웹 거래 인터페이스 구현을 위한 완전한 UX/UI 가이드입니다.*