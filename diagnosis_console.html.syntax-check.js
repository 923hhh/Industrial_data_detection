

  // ============================================================
  // 配置：后端地址（需要与 uvicorn 端口一致）
  // ============================================================
  const BASE_URL_STORAGE_KEY = 'fault-diagnosis-base-url';
  const FALLBACK_BASE_URL = 'http://127.0.0.1:8000';
  const CONNECT_TIMEOUT_MS = 8000;

  // 配置 marked.js：使用 GFM（表格、删除线等）
  marked.use({
    gfm: true,
    breaks: true,
  });

  let es = null;
  let eventCount = 0;
  let connectTimeoutId = null;
  let streamConnected = false;

  // ============================================================
  // 发起诊断请求
  // ============================================================
  function initializePage() {
    const baseUrlInput = document.getElementById('baseUrl');
    baseUrlInput.value = getInitialBaseUrl();
  }

  function getInitialBaseUrl() {
    const saved = localStorage.getItem(BASE_URL_STORAGE_KEY);
    if (saved) {
      return saved;
    }

    if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
      return window.location.origin;
    }

    return FALLBACK_BASE_URL;
  }

  function normalizeBaseUrl(rawValue) {
    const candidate = (rawValue || '').trim() || getInitialBaseUrl();

    let parsed;
    try {
      parsed = new URL(candidate);
    } catch {
      throw new Error('后端地址格式无效，请输入 http:// 或 https:// 开头的地址。');
    }

    if (!['http:', 'https:'].includes(parsed.protocol)) {
      throw new Error('后端地址只支持 http:// 或 https://。');
    }

    return parsed.href.replace(/\/$/, '');
  }

  function validateForm() {
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    const symptom = document.getElementById('symptom').value.trim();
    const modelName = document.getElementById('modelName').value.trim();
    const rawBaseUrl = document.getElementById('baseUrl').value;

    if (!startTime || !endTime) {
      throw new Error('请先填写完整的起始时间和结束时间。');
    }

    const startDate = new Date(startTime);
    const endDate = new Date(endTime);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
      throw new Error('时间格式无效，请使用页面提供的时间选择器。');
    }

    if (endDate <= startDate) {
      throw new Error('结束时间必须晚于起始时间。');
    }

    return {
      startTime,
      endTime,
      symptom,
      modelName,
      baseUrl: normalizeBaseUrl(rawBaseUrl),
    };
  }

  function formatDateTimeLocal(dateTimeLocal) {
    return dateTimeLocal.replace('T', ' ') + ':00';
  }

  function buildStreamUrl(payload) {
    const params = new URLSearchParams();
    params.set('start_time', payload.start_time);
    params.set('end_time', payload.end_time);
    params.set('model_provider', payload.model_provider);
    params.set('model_name', payload.model_name);
    if (payload.symptom_description) {
      params.set('symptom_description', payload.symptom_description);
    }
    return `/api/v1/diagnose/stream?${params.toString()}`;
  }

  function parseEventData(raw, fallback = {}) {
    if (raw === undefined || raw === null || raw === '') {
      return fallback;
    }

    try {
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  function setRunningState(isRunning) {
    document.getElementById('startBtn').disabled = isRunning;
  }

  function clearConnectTimeout() {
    if (connectTimeoutId) {
      clearTimeout(connectTimeoutId);
      connectTimeoutId = null;
    }
  }

  function closeStream() {
    clearConnectTimeout();
    if (es) {
      es.close();
      es = null;
    }
  }

  function handleClientError(message, detail = '') {
    if (detail) {
      log(`[错误详情] ${detail}`, 'event-error');
    }
    log(`[错误] ${message}`, 'event-error');
    setStatus('● 错误', 'error');
    setRunningState(false);
    closeStream();
  }

  function scheduleConnectTimeout(baseUrl) {
    clearConnectTimeout();
    connectTimeoutId = setTimeout(() => {
      if (!streamConnected && es) {
        handleClientError(
          '连接超时，8 秒内未收到服务确认。',
          `请检查后端地址 ${baseUrl}、服务是否已启动，以及浏览器是否能访问该地址。`
        );
      }
    }, CONNECT_TIMEOUT_MS);
  }

  function startDiagnosis() {
    let formData;
    try {
      formData = validateForm();
    } catch (error) {
      clearTerminal();
      handleClientError(error.message);
      return;
    }

    clearTerminal();
    setStatus('● 连接中...', '');
    setRunningState(true);
    streamConnected = false;

    const payload = {
      start_time: formatDateTimeLocal(formData.startTime),
      end_time: formatDateTimeLocal(formData.endTime),
      symptom_description: formData.symptom || null,
      model_provider: 'openai',
      model_name: formData.modelName || 'deepseek-chat'
    };

    // 拼接 SSE URL（GET 方式，query 参数）
    const url = buildStreamUrl(payload);
    localStorage.setItem(BASE_URL_STORAGE_KEY, formData.baseUrl);

    log('开始连接 SSE 流式端点...', 'event-timestamp');
    log(`后端地址: ${formData.baseUrl}`, 'event-timestamp');
    log(`请求地址: ${url}`, 'event-timestamp');
    log(`时间范围: ${payload.start_time} ~ ${payload.end_time}`, 'event-timestamp');
    log('---', 'event-timestamp');

    // 关闭已有连接
    closeStream();

    es = new EventSource(new URL(url, `${formData.baseUrl}/`).toString());
    scheduleConnectTimeout(formData.baseUrl);

    es.addEventListener('connected', (e) => {
      streamConnected = true;
      clearConnectTimeout();
      const raw = (e.data === undefined || e.data === null) ? '{}' : e.data;
      let data;
      try { data = JSON.parse(raw); } catch { data = raw; }
      const status = (typeof data === 'object' && data !== null) ? data.status : data;
      log(`[连接成功] ${status}`, 'event-timestamp');
      setStatus('● 诊断中...', 'connected');
    });

    es.addEventListener('node_start', (e) => {
      const d = parseEventData(e.data, { node: 'unknown', message: '节点开始执行' });
      log(`[节点开始] ${d.node} → ${d.message}`, 'event-node_start');
      eventCount++;
      document.getElementById('eventCount').textContent = `已接收事件: ${eventCount}`;
    });

    es.addEventListener('node_finish', (e) => {
      const d = parseEventData(e.data, { node: 'unknown', status: 'done' });
      const extra = d.preview ? ` | ${d.preview.slice(0, 60)}...` :
                    d.next     ? ` | 下一步: ${d.next}` : '';
      log(`[节点完成] ${d.node}${extra}`, 'event-node_finish');
      eventCount++;
      document.getElementById('eventCount').textContent = `已接收事件: ${eventCount}`;
    });

    es.addEventListener('report', (e) => {
      const d = parseEventData(e.data, { report: '报告为空。' });
      logReport(d.report);
      eventCount++;
      document.getElementById('eventCount').textContent = `已接收事件: ${eventCount}`;
    });

    es.addEventListener('error', (e) => {
      const d = parseEventData(e.data, { error: '服务端返回了错误事件。' });
      handleClientError(d.error);
    });

    es.addEventListener('done', (e) => {
      log(`\n[流式响应结束] ${e.data}`, 'event-done');
      setStatus('● 完成', 'connected');
      setRunningState(false);
      closeStream();
    });

    es.onerror = () => {
      const detail = streamConnected
        ? '连接在建立后中断，请检查后端日志、网络代理或接口报错。'
        : '请确认后端服务已启动、地址可访问，并检查浏览器控制台是否存在跨域或网络错误。';
      handleClientError('SSE 连接中断或服务器不可达。', detail);
    };
  }

  // ============================================================
  // 工具函数
  // ============================================================
  function log(text, cls) {
    const term = document.getElementById('terminal');
    const p = document.createElement('p');
    p.className = cls;
    p.textContent = text;
    term.appendChild(p);
    term.scrollTop = term.scrollHeight;

    // 打字机效果：给 report 类型动态加光标
    if (cls === 'event-report' && !term.querySelector('.cursor')) {
      const cur = document.createElement('span');
      cur.className = 'cursor';
      p.appendChild(cur);
      setTimeout(() => cur.remove(), 2000);
    }
  }

  /** 将诊断报告渲染为 Markdown（使用 marked.js） */
  function logReport(markdownText) {
    const term = document.getElementById('terminal');

    // 顶部装饰分隔
    const divider = document.createElement('p');
    divider.className = 'report-divider';
    divider.textContent = '━━━ 诊 断 报 告 ━━━';
    term.appendChild(divider);

    // 渲染 Markdown 为 HTML
    const html = marked.parse(markdownText || '');

    // 创建报告容器
    const container = document.createElement('div');
    container.className = 'md-report';
    container.innerHTML = html;
    term.appendChild(container);

    // 底部装饰
    const end = document.createElement('p');
    end.className = 'report-divider';
    end.textContent = '━━━━━━━━━━━━━━━━━━━━━';
    term.appendChild(end);

    term.scrollTop = term.scrollHeight;
  }

  function setStatus(text, cls) {
    const el = document.getElementById('status');
    el.textContent = text;
    el.className = cls || '';
  }

  function clearTerminal() {
    const term = document.getElementById('terminal');
    term.innerHTML = '';
    eventCount = 0;
    document.getElementById('eventCount').textContent = '已接收事件: 0';
    setStatus('● 就绪', '');
    setRunningState(false);
    streamConnected = false;
    closeStream();
  }

  initializePage();
