import { useState } from "react";
import type { ProviderChoice, ProviderDescriptor } from "@/api/types";
import { hasOptions } from "@/features/providers/chain";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { Badge, Button, IconButton, Switch } from "@/shared/ui";

interface ChainRowProps {
  index: number;
  total: number;
  choice: ProviderChoice;
  descriptor: ProviderDescriptor | undefined;
  onChange: (patch: Partial<ProviderChoice>) => void;
  onMove: (delta: -1 | 1) => void;
  onRemove: () => void;
}

function Availability({ descriptor }: { descriptor: ProviderDescriptor | undefined }) {
  if (descriptor === undefined) {
    return <Badge tone="danger">Not installed</Badge>;
  }
  return (
    <span className="row">
      <Badge tone={descriptor.available ? "success" : "danger"} dot>
        {descriptor.available ? "Available" : "Unavailable"}
      </Badge>
      <Badge>{descriptor.offline ? "Runs offline" : "Uses the internet"}</Badge>
      {descriptor.required_secrets.map((secret) => (
        <Badge key={secret} tone="info">
          Needs {secret}
        </Badge>
      ))}
    </span>
  );
}

function ChainInfo({
  name,
  descriptor,
}: {
  name: string;
  descriptor: ProviderDescriptor | undefined;
}) {
  return (
    <div className="chain-info">
      <span className="cell-title">{name}</span>
      {descriptor?.description && <span className="subtle">{descriptor.description}</span>}
      <Availability descriptor={descriptor} />
      {descriptor && !descriptor.available && descriptor.unavailable_reason && (
        <span className="field-error">{descriptor.unavailable_reason}</span>
      )}
    </div>
  );
}

function ChainControls({
  name,
  index,
  total,
  choice,
  onChange,
  onMove,
  onRemove,
}: Omit<ChainRowProps, "descriptor"> & { name: string }) {
  return (
    <div className="chain-controls">
      <Switch
        checked={choice.enabled}
        ariaLabel={`Use ${name}`}
        onChange={(enabled) => onChange({ enabled })}
      />
      <IconButton
        icon="up"
        label={`Move ${name} up`}
        disabled={index === 0}
        onClick={() => onMove(-1)}
      />
      <IconButton
        icon="down"
        label={`Move ${name} down`}
        disabled={index === total - 1}
        onClick={() => onMove(1)}
      />
      <IconButton icon="trash" variant="danger" label={`Remove ${name}`} onClick={onRemove} />
    </div>
  );
}

function ChainOptions({
  descriptor,
  choice,
  onChange,
}: {
  descriptor: ProviderDescriptor;
  choice: ProviderChoice;
  onChange: (patch: Partial<ProviderChoice>) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="chain-options">
      <Button
        size="sm"
        variant="ghost"
        icon={open ? "up" : "down"}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? "Hide options" : "Options"}
      </Button>
      {open && (
        <SchemaForm
          idPrefix={`provider-${descriptor.provider_id}`}
          schema={descriptor.options_schema}
          value={choice.options}
          onChange={(options) => onChange({ options })}
        />
      )}
    </div>
  );
}

export function ChainRow(props: ChainRowProps) {
  const { choice, descriptor } = props;
  const name = descriptor?.name ?? choice.provider_id;
  const rowClass = choice.enabled ? "chain-row panel-inset" : "chain-row panel-inset chain-row-off";
  return (
    <li className={rowClass} aria-label={name}>
      <div className="chain-head">
        <span className="chain-position" aria-hidden="true">
          {props.index + 1}
        </span>
        <ChainInfo name={name} descriptor={descriptor} />
        <ChainControls {...props} name={name} />
      </div>
      {descriptor && hasOptions(descriptor) && (
        <ChainOptions descriptor={descriptor} choice={choice} onChange={props.onChange} />
      )}
    </li>
  );
}
