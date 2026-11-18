import type { ReactNode } from "react";
import type { FieldErrors } from "@/api/errors";
import type { AppSettingName, AppSettings } from "@/api/types";
import { RESTART_NOTE, SETTING_TEXT, settingNote } from "@/features/app-settings/fieldText";
import { Badge, FormField } from "@/shared/ui";

interface SettingFieldProps {
  name: AppSettingName;
  settings: AppSettings;
  errors: FieldErrors;
  children: (locked: boolean) => ReactNode;
}

function SettingLabel({
  name,
  locked,
  restart,
}: {
  name: AppSettingName;
  locked: boolean;
  restart: boolean;
}) {
  return (
    <span className="setting-label">
      {SETTING_TEXT[name].label}
      {restart && <Badge tone="info">{RESTART_NOTE}</Badge>}
      {locked && <Badge tone="warning">Locked</Badge>}
    </span>
  );
}

export function SettingField({ name, settings, errors, children }: SettingFieldProps) {
  const note = settingNote(settings, name);
  const locked = note.locked !== undefined;
  const hint = (
    <>
      {SETTING_TEXT[name].hint}
      {locked && <span className="setting-lock">{note.locked}</span>}
    </>
  );
  return (
    <FormField
      label={<SettingLabel name={name} locked={locked} restart={note.restart} />}
      hint={hint}
      error={errors[name]}
    >
      {children(locked)}
    </FormField>
  );
}
