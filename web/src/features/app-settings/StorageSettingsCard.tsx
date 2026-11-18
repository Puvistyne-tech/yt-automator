import type { ReactNode } from "react";
import {
  AutoCleanupSetting,
  NumberSetting,
  type SettingsCardProps,
} from "@/features/app-settings/SettingControls";
import { Card } from "@/shared/ui";

interface StorageSettingsCardProps extends SettingsCardProps {
  usage?: ReactNode;
}

export function StorageSettingsCard({ usage, ...card }: StorageSettingsCardProps) {
  return (
    <Card
      title="Storage and cleanup"
      description="How long runs and their files are kept, and how much space they use."
    >
      <div className="stack">
        <div className="grid-2">
          <NumberSetting {...card} name="keep_runs_days" min={0} />
          <NumberSetting {...card} name="keep_intermediate_days" min={0} />
        </div>
        <div className="grid-2">
          <AutoCleanupSetting {...card} />
          <NumberSetting {...card} name="cleanup_interval_hours" min={0} />
        </div>
        {usage}
      </div>
    </Card>
  );
}
