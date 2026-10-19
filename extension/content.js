const ALLOWED_PORTAL_ORIGINS = new Set([
  'http://localhost:5500',
  'http://127.0.0.1:5500',
  globalThis.ZERO_KEY_CONFIG?.portalOrigin,
]);
const WINDOW_DURATION_MS = 15_000;
const PAUSE_THRESHOLD_MS = 500;
const SESSION_IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const SESSION_STORAGE_KEY = 'zerokey_portal_session';
let collectorStatus = 'Extension loaded. Waiting for activity.';
let statusElement = null;
let collectorStatusObserver = null;

function setCollectorStatus(message) {
  if (collectorStatus === message) {
    return;
  }
  collectorStatus = message;
  if (statusElement) {
    statusElement.textContent = message;
  }
}

function connectCollectorStatus() {
  statusElement = document.getElementById('telemetry-status');
  if (statusElement) {
    statusElement.textContent = collectorStatus;
    collectorStatusObserver?.disconnect();
    collectorStatusObserver = null;
  } else if (!collectorStatusObserver && document.documentElement) {
    collectorStatusObserver = new MutationObserver(() => {
      statusElement = document.getElementById('telemetry-status');
      if (statusElement) {
        statusElement.textContent = collectorStatus;
        collectorStatusObserver.disconnect();
        collectorStatusObserver = null;
      }
    });
    collectorStatusObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }
}

function createPortalSession(now) {
  try {
    const storedValue = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (storedValue) {
      const storedSession = JSON.parse(storedValue);
      if (
        typeof storedSession.id === 'string' &&
        typeof storedSession.lastActivityAt === 'number' &&
        now - storedSession.lastActivityAt <= SESSION_IDLE_TIMEOUT_MS
      ) {
        return {
          id: storedSession.id,
          lastActivityAt: storedSession.lastActivityAt,
          lastPersistedAt: storedSession.lastActivityAt,
        };
      }
    }

    const session = {
      id: crypto.randomUUID(),
      lastActivityAt: now,
      lastPersistedAt: now,
    };
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
    return session;
  } catch (error) {
    console.error('Unable to initialize the portal session ID.', error);
    return null;
  }
}

let portalSession = null;
const heldKeys = new Map();

let previousMouse = null;
let mouseBurstStart = null;
let mouseBurstEnd = null;
let mouseDisplacement = 0;
let previousDirection = null;
let mousePathLength = 0;
let mouseActiveDuration = 0;
let directionChanges = 0;
let mouseMoveCount = 0;
let clickCount = 0;
let lastClickAt = null;
let clickIntervals = [];

let keyDownCount = 0;
let overlappingKeyDownCount = 0;
let lastKeyDownAt = null;
let lastKeyUpAt = null;
let keyboardActiveDuration = 0;
let dwellTimes = [];
let releasePressIntervals = [];
let pressPressIntervals = [];
let keyIntervals = [];
let pauseDurations = [];

function markPortalActivity() {
  if (!portalSession) {
    portalSession = createPortalSession(Date.now());
    if (!portalSession) {
      setCollectorStatus('Could not initialize a portal session. Check browser storage settings.');
      return false;
    }
  }

  setCollectorStatus('Activity detected. A feature summary will send within 15 seconds.');
  const now = Date.now();
  if (now - portalSession.lastActivityAt > SESSION_IDLE_TIMEOUT_MS) {
    heldKeys.clear();
    clearWindowFeatures();
    portalSession.id = crypto.randomUUID();
  }
  portalSession.lastActivityAt = now;

  if (now - portalSession.lastPersistedAt >= 60_000) {
    try {
      sessionStorage.setItem(
        SESSION_STORAGE_KEY,
        JSON.stringify({
          id: portalSession.id,
          lastActivityAt: now,
        }),
      );
      portalSession.lastPersistedAt = now;
    } catch (error) {
      console.error('Unable to update the portal session activity time.', error);
      return false;
    }
  }

  return true;
}

function mean(values) {
  if (values.length === 0) {
    return null;
  }
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function standardDeviation(values) {
  if (values.length === 0) {
    return null;
  }

  const average = mean(values);
  const variance =
    values.reduce((total, value) => total + (value - average) ** 2, 0) /
    values.length;
  return Math.sqrt(variance);
}

function onMouseMove(event) {
  if (!markPortalActivity()) {
    return;
  }

  const point = {
    x: event.clientX,
    y: event.clientY,
    at: performance.now(),
  };
  mouseMoveCount += 1;
  if (!mouseBurstStart) {
    mouseBurstStart = point;
  }

  if (previousMouse) {
    const dx = point.x - previousMouse.x;
    const dy = point.y - previousMouse.y;
    const distance = Math.hypot(dx, dy);
    const elapsed = point.at - previousMouse.at;

    if (elapsed > 2_000) {
      mouseDisplacement += Math.hypot(
        mouseBurstEnd.x - mouseBurstStart.x,
        mouseBurstEnd.y - mouseBurstStart.y,
      );
      mouseBurstStart = point;
      previousDirection = null;
    } else if (distance > 0 && elapsed > 0) {
      mousePathLength += distance;
      mouseActiveDuration += elapsed;

      const direction = Math.atan2(dy, dx);
      if (previousDirection !== null) {
        let angleChange = Math.abs(direction - previousDirection);
        if (angleChange > Math.PI) {
          angleChange = 2 * Math.PI - angleChange;
        }
        if (angleChange >= Math.PI / 4) {
          directionChanges += 1;
        }
      }
      previousDirection = direction;
    }
  }

  mouseBurstEnd = point;
  previousMouse = point;
}

function onClick() {
  if (!markPortalActivity()) {
    return;
  }

  const now = performance.now();
  clickCount += 1;
  if (lastClickAt !== null) {
    const interval = now - lastClickAt;
    if (interval <= 2_000) {
      clickIntervals.push(interval);
    }
  }
  lastClickAt = now;
}

function onKeyDown(event) {
  if (!markPortalActivity() || event.repeat || heldKeys.has(event.code)) {
    return;
  }

  const now = performance.now();
  if (heldKeys.size > 0) {
    overlappingKeyDownCount += 1;
  }
  heldKeys.set(event.code, now);
  keyDownCount += 1;

  if (lastKeyDownAt !== null) {
    const interval = now - lastKeyDownAt;
    if (interval >= PAUSE_THRESHOLD_MS) {
      pauseDurations.push(interval);
    } else {
      keyboardActiveDuration += interval;
      keyIntervals.push(interval);
      pressPressIntervals.push(interval);
    }
  }
  if (lastKeyUpAt !== null) {
    const interval = now - lastKeyUpAt;
    if (interval >= 0 && interval < PAUSE_THRESHOLD_MS) {
      releasePressIntervals.push(interval);
    }
  }
  lastKeyDownAt = now;
}

function onKeyUp(event) {
  const pressedAt = heldKeys.get(event.code);
  if (pressedAt === undefined || !markPortalActivity()) {
    return;
  }

  const now = performance.now();
  dwellTimes.push(now - pressedAt);
  heldKeys.delete(event.code);
  lastKeyUpAt = now;
}

function clearWindowFeatures() {
  previousMouse = null;
  mouseBurstStart = null;
  mouseBurstEnd = null;
  mouseDisplacement = 0;
  previousDirection = null;
  mousePathLength = 0;
  mouseActiveDuration = 0;
  directionChanges = 0;
  mouseMoveCount = 0;
  clickCount = 0;
  lastClickAt = null;
  clickIntervals = [];
  keyDownCount = 0;
  overlappingKeyDownCount = 0;
  lastKeyDownAt = null;
  lastKeyUpAt = null;
  keyboardActiveDuration = 0;
  dwellTimes = [];
  releasePressIntervals = [];
  pressPressIntervals = [];
  keyIntervals = [];
  pauseDurations = [];
}

function sendWindowFeatures() {
  const hasActivity =
    mouseMoveCount > 0 || clickCount > 0 || keyDownCount > 0 || dwellTimes.length > 0;

  if (!hasActivity || !portalSession) {
    clearWindowFeatures();
    return;
  }

  const displacement =
    mouseDisplacement +
    (mouseBurstStart && mouseBurstEnd
      ? Math.hypot(
          mouseBurstEnd.x - mouseBurstStart.x,
          mouseBurstEnd.y - mouseBurstStart.y,
        )
      : 0);
  const payload = {
    collection_version: 2,
    session_id: portalSession.id,
    timestamp: new Date().toISOString(),
    mouse_features: {
      path_length_px: mousePathLength,
      displacement_px: displacement,
      average_velocity_px_per_second:
        mouseActiveDuration > 0 ? mousePathLength / (mouseActiveDuration / 1000) : 0,
      direction_changes_per_second:
        mouseActiveDuration > 0
          ? directionChanges / (mouseActiveDuration / 1000)
          : 0,
      straightness_ratio:
        mousePathLength > 0
          ? Math.min(1, displacement / mousePathLength)
          : null,
      click_interval_ms_mean: mean(clickIntervals),
    },
    keyboard_features: {
      dwell_time_ms_mean: mean(dwellTimes),
      pp_latency_ms_mean: mean(pressPressIntervals),
      rp_latency_ms_mean: mean(releasePressIntervals),
      typing_rate_keystrokes_per_minute:
        keyboardActiveDuration > 0
          ? keyDownCount / (keyboardActiveDuration / 60_000)
          : 0,
      pause_count: pauseDurations.length,
      pause_duration_ms_mean: mean(pauseDurations),
      inter_key_interval_ms_stddev: standardDeviation(keyIntervals),
      dwell_time_ms_stddev: standardDeviation(dwellTimes),
      pp_latency_ms_stddev: standardDeviation(pressPressIntervals),
      rp_latency_ms_stddev: standardDeviation(releasePressIntervals),
      rollover_ratio:
        keyDownCount > 0 ? overlappingKeyDownCount / keyDownCount : 0,
    },
  };

  setCollectorStatus('Activity captured. Sending feature summary...');
  chrome.runtime.sendMessage({ type: 'telemetry-window', payload }).then(
    (response) => {
      if (response?.ok) {
        setCollectorStatus('Feature summary accepted by the configured API.');
      } else {
        const error = response?.error ?? 'The extension rejected the telemetry message.';
        setCollectorStatus(`Could not send telemetry: ${error}`);
        console.error('Behavioral telemetry was not accepted by the extension service worker.', error);
      }
    },
    (error) => {
      setCollectorStatus('Could not reach the extension service worker. Reload the extension.');
      console.error('Unable to contact the extension service worker.', error);
    },
  );

  clearWindowFeatures();
}

function startCollector() {
  if (!ALLOWED_PORTAL_ORIGINS.has(window.location.origin)) {
    return;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectCollectorStatus, { once: true });
  } else {
    connectCollectorStatus();
  }
  document.addEventListener('mousemove', onMouseMove, { passive: true });
  document.addEventListener('click', onClick, { passive: true });
  document.addEventListener('keydown', onKeyDown, { passive: true });
  document.addEventListener('keyup', onKeyUp, { passive: true });
  window.addEventListener('blur', () => heldKeys.clear());
  window.setInterval(sendWindowFeatures, WINDOW_DURATION_MS);
}

if (ALLOWED_PORTAL_ORIGINS.has(window.location.origin)) {
  connectCollectorStatus();
  chrome.runtime.sendMessage({ type: 'telemetry-ready' }).then(
    (response) => {
      if (response?.ok) {
        startCollector();
      } else {
        setCollectorStatus(response?.error ?? 'Sign in from the extension popup to enable collection.');
      }
    },
    (error) => {
      console.error('Unable to check extension sign-in status.', error);
      setCollectorStatus('Could not verify extension sign-in. Reload the portal after signing in.');
    },
  );
}
