import { useId } from "react";
import { useCities } from "../api/client";

interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

// Free text with suggestions from the backend's city list.
export default function CityInput({ label, value, onChange, placeholder }: Props) {
  const id = useId();
  const { data } = useCities(value.length >= 1 ? value : "");
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      <input
        id={id}
        className="input"
        list={`${id}-list`}
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        onChange={(e) => onChange(e.target.value)}
        required
      />
      <datalist id={`${id}-list`}>
        {data?.map((c) => (
          <option key={c.name} value={c.name}>
            {c.state}, {c.country}
          </option>
        ))}
      </datalist>
    </div>
  );
}
