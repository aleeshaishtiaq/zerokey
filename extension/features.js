// Feature set v2 (mouse kinematics) and mouse v3 (strokes) for one 15-second
// window. The formulas match src/data_pipeline/prepare_training_windows.py
// (MouseWindow, summarize_stroke, stroke_features), so live windows and the
// training data are computed the same way. tests/test_extension_parity.py
// checks this with node.
(function (root) {
  const STROKE_GAP_MS = 300;
  const MIN_STROKE_SAMPLES = 4;
  const MIN_STROKE_PX = 10;
  const CLICK_AFTER_STROKE_MS = 1_000;

  function mean(values) {
    return values.length ? values.reduce((total, value) => total + value, 0) / values.length : null;
  }

  function standardDeviation(values) {
    if (!values.length) {
      return null;
    }
    const average = mean(values);
    return Math.sqrt(values.reduce((total, value) => total + (value - average) ** 2, 0) / values.length);
  }

  function quantile(values, fraction) {
    if (!values.length) {
      return null;
    }
    const sorted = [...values].sort((a, b) => a - b);
    const position = (sorted.length - 1) * fraction;
    const lower = Math.floor(position);
    const upper = Math.ceil(position);
    return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
  }

  const median = (values) => quantile(values, 0.5);
  const p90 = (values) => quantile(values, 0.9);

  function summarizeStroke(points) {
    if (points.length < MIN_STROKE_SAMPLES) {
      return null;
    }
    const lengths = [];
    for (let index = 1; index < points.length; index += 1) {
      lengths.push(Math.hypot(points[index].x - points[index - 1].x, points[index].y - points[index - 1].y));
    }
    const path = lengths.reduce((total, value) => total + value, 0);
    const first = points[0];
    const last = points[points.length - 1];
    const duration = last.at - first.at;
    if (path < MIN_STROKE_PX || duration <= 0) {
      return null;
    }
    const dx = last.x - first.x;
    const dy = last.y - first.y;
    const displacement = Math.hypot(dx, dy);
    let deviation = 0;
    if (displacement > 0) {
      for (const point of points.slice(1, -1)) {
        const cross = Math.abs(dx * (point.y - first.y) - dy * (point.x - first.x));
        deviation = Math.max(deviation, cross / displacement);
      }
    }
    let turning = 0;
    let previousAngle = null;
    let peakSpeed = 0;
    let peakAt = first.at;
    for (let index = 1; index < points.length; index += 1) {
      const length = lengths[index - 1];
      if (length <= 0) {
        continue;
      }
      const a = points[index - 1];
      const b = points[index];
      const angle = Math.atan2(b.y - a.y, b.x - a.x);
      if (previousAngle !== null) {
        const change = Math.abs(angle - previousAngle);
        turning += change > Math.PI ? 2 * Math.PI - change : change;
      }
      previousAngle = angle;
      const elapsed = b.at - a.at;
      if (elapsed > 0 && (length / elapsed) * 1000 > peakSpeed) {
        peakSpeed = (length / elapsed) * 1000;
        peakAt = b.at;
      }
    }
    return {
      end: last.at,
      duration,
      length: path,
      efficiency: Math.min(1, displacement / path),
      deviation: deviation / path,
      curvature: turning / path,
      peakSpeed,
      timeToPeak: (peakAt - first.at) / duration,
      horizontal: Math.abs(dx) >= Math.abs(dy),
      pauseBeforeClick: null,
    };
  }

  function strokeFeatures(strokes) {
    const values = (key) => strokes.map((stroke) => stroke[key]).filter((value) => value !== null);
    const pauses = values('pauseBeforeClick');
    const count = strokes.length;
    return {
      stroke_count: count,
      stroke_duration_ms_median: median(values('duration')),
      stroke_length_px_median: median(values('length')),
      stroke_efficiency_mean: mean(values('efficiency')),
      stroke_efficiency_median: median(values('efficiency')),
      stroke_deviation_ratio_median: median(values('deviation')),
      stroke_curvature_rad_per_px_median: median(values('curvature')),
      stroke_peak_speed_px_per_second_median: median(values('peakSpeed')),
      stroke_time_to_peak_ratio_median: median(values('timeToPeak')),
      stroke_horizontal_share: count ? strokes.filter((stroke) => stroke.horizontal).length / count : null,
      click_stroke_share: count ? pauses.length / count : null,
      pause_before_click_ms_median: median(pauses),
    };
  }

  // Extra mouse state for one window; content.js calls it from its handlers
  // in the same order as MouseWindow.move / click / right_click in Python.
  function createMouseExtras() {
    let lastSpeed = null;
    let lastAcceleration = null;
    let strokePoints = [];
    const speeds = [];
    const accelerations = [];
    const jerks = [];
    const strokes = [];
    let rightClicks = 0;

    function endStroke() {
      const stroke = summarizeStroke(strokePoints);
      if (stroke) {
        strokes.push(stroke);
      }
      strokePoints = [];
    }

    return {
      addPoint(point) {
        if (strokePoints.length && point.at - strokePoints[strokePoints.length - 1].at > STROKE_GAP_MS) {
          endStroke();
        }
        strokePoints.push(point);
      },
      resetKinematics() {
        lastSpeed = null;
        lastAcceleration = null;
      },
      kinematics(distance, elapsed) {
        const seconds = elapsed / 1000;
        const speed = distance / seconds;
        speeds.push(speed);
        if (lastSpeed !== null) {
          const acceleration = Math.abs(speed - lastSpeed) / seconds;
          accelerations.push(acceleration);
          if (lastAcceleration !== null) {
            jerks.push(Math.abs(acceleration - lastAcceleration) / seconds);
          }
          lastAcceleration = acceleration;
        }
        lastSpeed = speed;
      },
      click(at) {
        endStroke();
        if (strokes.length) {
          const last = strokes[strokes.length - 1];
          const pause = at - last.end;
          if (last.pauseBeforeClick === null && pause >= 0 && pause <= CLICK_AFTER_STROKE_MS) {
            last.pauseBeforeClick = pause;
          }
        }
      },
      rightClick() {
        rightClicks += 1;
      },
      features() {
        const open = summarizeStroke(strokePoints);
        return {
          speed_px_per_second_std: standardDeviation(speeds),
          speed_px_per_second_median: median(speeds),
          speed_px_per_second_p90: p90(speeds),
          acceleration_px_per_second2_mean: mean(accelerations),
          acceleration_px_per_second2_std: standardDeviation(accelerations),
          acceleration_px_per_second2_p90: p90(accelerations),
          jerk_px_per_second3_mean: mean(jerks),
          jerk_px_per_second3_median: median(jerks),
          jerk_px_per_second3_p90: p90(jerks),
          right_click_count: rightClicks,
          ...strokeFeatures(open ? strokes.concat([open]) : strokes),
        };
      },
    };
  }

  const api = { mean, standardDeviation, median, p90, summarizeStroke, strokeFeatures, createMouseExtras };
  root.ZeroKeyFeatures = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(globalThis);
