export function TelemetryFeatureValues({
  values,
}: {
  values: Record<string, number | null>;
}) {
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
