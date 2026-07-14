import { BackgroundPicker } from "./BackgroundPicker";

interface AvatarValue {
  bg_kind: "solid" | "gradient";
  bg_color?: string;
  bg_gradient?: { from: string; to: string; angle: number };
}

interface Props {
  value: AvatarValue;
  onChange: (next: AvatarValue) => void;
}

export function AvatarColorPicker({ value, onChange }: Props) {
  return <BackgroundPicker value={value} onChange={onChange} compact />;
}
