import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useAuth0 } from '@auth0/auth0-react';
import { TopBar } from '../components/layout/TopBar';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8765')
  .replace(/\/+$/, '');
const TELEMETRY_API_URL = `${API_BASE_URL}/api/telemetry/recent?limit=50`;

interface TelemetryRecord {
  device_id: string;
  session_id: string;
  timestamp: string;
  public_ip_address: string | null;
  mouse_features: Record<string, number | null>;
  keyboard_features: Record<string, number | null>;
}

export function TelemetryPage() {
  const { getAccessTokenSilently } = useAuth0();
  const [records, setRecords] = useState<TelemetryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const accessToken = await getAccessTokenSilently();
      const response = await fetch(TELEMETRY_API_URL, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) {
        throw new Error(`Telemetry API returned HTTP ${response.status}.`);
      }
      const recentRecords = (await response.json()) as TelemetryRecord[];
      setRecords(recentRecords);
      setLastUpdated(new Date());
      setError('');
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : 'Unable to load telemetry records.',
      );
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return (
    <>
      <TopBar title="Recent Telemetry" />
      <div className="app-page">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Captured behavioral windows</h2>
            <p className="text-sm text-gray-500">
              Refreshes automatically every 5 seconds.
              {lastUpdated && ` Last updated ${lastUpdated.toLocaleTimeString()}.`}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-wait disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && (
          <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error} Check that the configured FastAPI API is reachable.
          </p>
        )}

        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Device ID (SHA-256)</th>
                <th className="px-4 py-3">Session ID</th>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Public IP (ipify)</th>
                <th className="px-4 py-3">Mouse features</th>
                <th className="px-4 py-3">Keyboard features</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={`${record.session_id}-${record.timestamp}`} className="border-b border-gray-50 align-top">
                  <td className="max-w-48 break-all px-4 py-3 font-mono text-xs">{record.device_id}</td>
                  <td className="max-w-40 break-all px-4 py-3 font-mono text-xs">{record.session_id}</td>
                  <td className="whitespace-nowrap px-4 py-3">{new Date(record.timestamp).toLocaleString()}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs">
                    {record.public_ip_address ?? 'Not available'}
                  </td>
                  <td className="min-w-64 px-4 py-3">
                    <FeatureValues values={record.mouse_features} />
                  </td>
                  <td className="min-w-64 px-4 py-3">
                    <FeatureValues values={record.keyboard_features} />
                  </td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-gray-500">
                    {loading ? 'Loading telemetry…' : 'No telemetry records have been captured yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function FeatureValues({ values }: { values: Record<string, number | null> }) {
  return (
    <dl className="grid grid-cols-1 gap-y-1">
      {Object.entries(values).map(([name, value]) => (
        <div key={name} className="flex justify-between gap-3">
          <dt className="text-xs text-gray-500">{name.replace(/_/g, ' ')}</dt>
          <dd className="font-mono text-xs text-gray-800">{value === null ? '—' : value}</dd>
        </div>
      ))}
    </dl>
  );
}
