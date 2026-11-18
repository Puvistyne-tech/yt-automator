import type { IconButtonProps } from "@rjsf/utils";
import { IconButton } from "@/shared/ui/Button";
import type { IconName } from "@/shared/ui/Icon";

function SchemaIconButton({
  props,
  icon,
  label,
  danger = false,
}: {
  props: IconButtonProps;
  icon: IconName;
  label: string;
  danger?: boolean;
}) {
  return (
    <IconButton
      icon={icon}
      label={label}
      variant={danger ? "danger" : "ghost"}
      {...(props.id === undefined ? {} : { id: props.id })}
      disabled={props.disabled}
      onClick={props.onClick}
    />
  );
}

export function MoveUpButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="up" label="Move up" />;
}

export function MoveDownButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="down" label="Move down" />;
}

export function CopyButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="copy" label="Duplicate" />;
}

export function RemoveButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="trash" label="Remove" danger />;
}
