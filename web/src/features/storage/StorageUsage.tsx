import { useState } from "react";
import { useStorage } from "@/api/storage";
import type { StorageReport } from "@/api/types";
import { CleanupDialog } from "@/features/storage/CleanupDialog";
import { usageSummary } from "@/features/storage/model";
import { formatBytes, formatNumber } from "@/shared/format/numbers";
import { Button, EmptyState, ProgressMeter, QueryState, StatCard, Table } from "@/shared/ui";
import "@/features/storage/storage.css";

function UsageStats({ report }: { report: StorageReport }) {
  const summary = usageSummary(report);
  return (
    <div className="storage-stats">
      <StatCard label="Data folder" value={formatBytes(report.data_dir_bytes)} />
      <StatCard
        label="Final outputs"
        value={formatBytes(report.final_bytes)}
        hint={`${summary.final_share}% of run files`}
      />
      <StatCard
        label="Working files"
        value={formatBytes(summary.working_bytes)}
        hint={summary.stray_hint}
      />
      <StatCard label="Free space" value={summary.free_label} />
    </div>
  );
}

function DiskMeter({ report }: { report: StorageReport }) {
  if (report.disk_bytes === null || report.free_bytes === null) {
    return null;
  }
  const used = report.disk_bytes - report.free_bytes;
  return (
    <ProgressMeter
      label="Disk in use"
      value={used}
      max={report.disk_bytes}
      detail={`${formatBytes(used)} of ${formatBytes(report.disk_bytes)}`}
    />
  );
}

function AutomationTable({ report }: { report: StorageReport }) {
  if (report.automations.length === 0) {
    return <EmptyState title="No run files yet" description="Runs will show up here." />;
  }
  return (
    <Table
      label="Disk use per automation"
      columns={["Automation", "Runs", "Final outputs", "Working files"]}
    >
      {report.automations.map((usage) => (
        <tr key={usage.automation_id}>
          <td>{usage.automation_name}</td>
          <td>{formatNumber(usage.runs)}</td>
          <td>{formatBytes(usage.final_bytes)}</td>
          <td>{formatBytes(usage.intermediate_bytes)}</td>
        </tr>
      ))}
    </Table>
  );
}

export function StorageUsage() {
  const storage = useStorage();
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="stack storage-usage">
      <div className="row-between">
        <h3 className="storage-title">Disk use</h3>
        <Button icon="trash" onClick={() => setConfirming(true)}>
          Clean up now
        </Button>
      </div>
      <QueryState query={storage} loadingLabel="Measuring disk use">
        {(report) => (
          <>
            <UsageStats report={report} />
            <DiskMeter report={report} />
            <AutomationTable report={report} />
          </>
        )}
      </QueryState>
      <CleanupDialog open={confirming} onClose={() => setConfirming(false)} />
    </div>
  );
}
