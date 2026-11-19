export interface SettingFieldDefinition {
  key: string;
  label: string;
  description: string;
  type: "boolean" | "string" | "number" | "string[]" | "select";
  options?: { label: string; value: string }[];
  defaultValue?: any;
  placeholder?: string;
}

export interface SettingSectionDefinition {
  id: string;
  title: string;
  description?: string;
  fields: SettingFieldDefinition[];
}
