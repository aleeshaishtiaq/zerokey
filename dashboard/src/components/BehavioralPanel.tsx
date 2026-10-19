import type { BehavioralAnalysis, FeatureState } from '../types';
import { Badge } from './ui/Badge';

function featureVariant(state: FeatureState) {
  if (state === 'Normal') return 'success' as const;
  if (state === 'Slight Deviation') return 'warning' as const;
  return 'danger' as const;
}

const featureDescriptions: Record<string, string> = {
  'Dwell Time': 'Time between pressing and releasing the same key.',
  'Press-to-Press Latency': 'Time between two consecutive key presses.',
  'Release-to-Press Latency': 'Time between releasing one key and pressing the next key.',
  'Typing Rate': 'Valid key presses per unit of active typing time.',
  'Pause/Rhythm': 'Median, MAD, IQR, and long-pause ratio of typing pauses.',
  'Rollover Ratio': 'Transitions where the next key is pressed before the previous key is released.',
  'Path Length': 'Total distance travelled during mouse movement.',
  'Displacement': 'Direct distance from the first to the last mouse point.',
  'Velocity': 'Median, MAD, and 90th-percentile movement velocity.',
  'Direction Change Rate': 'Frequency of significant changes in movement direction.',
  'Straightness': 'Displacement divided by total path length.',
  'Click Interval': 'Time between consecutive click events.',
};

export function BehavioralPanel({ data }: { data: BehavioralAnalysis }) {
  const keyboard: [string, FeatureState][] = [
    ['Dwell Time', data.dwellTime],
    ['Press-to-Press Latency', data.ppLatency],
    ['Release-to-Press Latency', data.rpLatency],
    ['Typing Rate', data.typingRate],
    ['Pause/Rhythm', data.pauseRhythm],
    ['Rollover Ratio', data.rolloverRatio],
  ];

  const mouse: [string, FeatureState][] = [
    ['Path Length', data.mousePathLength],
    ['Displacement', data.mouseDisplacement],
    ['Velocity', data.mouseVelocity],
    ['Direction Change Rate', data.directionChangeRate],
    ['Straightness', data.straightness],
    ['Click Interval', data.clickInterval],
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 text-sm">
        <span className="rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-brand-800">
          Behavioral Monitoring: {data.monitoringActive ? 'Active' : 'Inactive'}
        </span>
        <span className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-gray-700">
          Current Analysis Window: Active
        </span>
        <span
          className={`rounded-lg border px-3 py-1.5 ${
            data.currentWindowAssessment === 'Normal'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
              : 'border-amber-200 bg-amber-50 text-amber-800'
          }`}
        >
          Latest Assessment: {data.currentWindowAssessment}
        </span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <FeatureTable title="Keyboard" rows={keyboard} />
        <FeatureTable title="Mouse" rows={mouse} />
      </div>
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-2 text-sm font-medium text-gray-900">Analysis Windows</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {data.analysisWindows.map((w, i) => (
            <Badge key={i} variant={w === 'Normal' ? 'success' : 'warning'}>
              Window {i + 1} — {w}
            </Badge>
          ))}
        </div>
        <p className="mt-3 text-sm text-gray-600">
          Consecutive Anomalous Windows:{' '}
          <span className="font-semibold text-gray-900">{data.consecutiveAnomalousWindows}</span>
        </p>
      </div>
    </div>
  );
}

function FeatureTable({ title, rows }: { title: string; rows: [string, FeatureState][] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
      </div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([name, state]) => (
            <tr key={name} className="border-b border-gray-50 last:border-0">
              <td className="px-4 py-2.5 text-gray-600" title={featureDescriptions[name]}>{name}</td>
              <td className="px-4 py-2.5 text-right">
                <Badge variant={featureVariant(state)}>{state}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
