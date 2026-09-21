import type { ChangeEvent } from "react";
import { useId } from "react";
import styles from "./RadioGroup.module.css";

export interface RadioOption {
  value: string;
  label: string;
}

export interface RadioGroupProps {
  legend: string;
  name?: string;
  options: RadioOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
}

/**
 * A `<fieldset>`/`<legend>` grouping real `<input type="radio">`
 * elements — native roving-tabindex and arrow-key navigation between
 * options come for free from the browser.
 */
export function RadioGroup({
  legend,
  name,
  options,
  value,
  defaultValue,
  onChange,
  disabled,
}: RadioGroupProps) {
  const generatedName = useId();
  const groupName = name ?? generatedName;

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onChange?.(event.target.value);
  }

  return (
    <fieldset className={styles.fieldset} disabled={disabled}>
      <legend className={styles.legend}>{legend}</legend>
      <div className={styles.options}>
        {options.map((option) => (
          <label key={option.value} className={styles.option}>
            <input
              type="radio"
              name={groupName}
              value={option.value}
              checked={value !== undefined ? value === option.value : undefined}
              defaultChecked={
                value === undefined && defaultValue !== undefined
                  ? defaultValue === option.value
                  : undefined
              }
              onChange={handleChange}
              className={styles.input}
            />
            <span className={styles.dot} aria-hidden="true" />
            <span className={styles.label}>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
