type StatusStripProps = {
  label: string;
};

export function StatusStrip({ label }: StatusStripProps) {
  return <div className="status-strip">{label}</div>;
}
