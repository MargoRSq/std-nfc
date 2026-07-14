import { useEffect, useRef, useState } from "react";
import { useWatch, type Control, type FieldValues, type Path } from "react-hook-form";
import { ChevronRight, X } from "lucide-react";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";

interface FioInputProps<T extends FieldValues> {
  control: Control<T>;
  lastNameField?: Path<T>;
  firstNameField?: Path<T>;
  middleNameField?: Path<T>;
}

export function FioInput<T extends FieldValues>({
  control,
  lastNameField = "last_name" as Path<T>,
  firstNameField = "first_name" as Path<T>,
  middleNameField = "middle_name" as Path<T>,
}: FioInputProps<T>) {
  const last = (useWatch({ control, name: lastNameField }) as string | undefined) ?? "";
  const first = (useWatch({ control, name: firstNameField }) as string | undefined) ?? "";
  const middle = (useWatch({ control, name: middleNameField }) as string | undefined) ?? "";

  const [value, setValue] = useState(() => [last, first, middle].filter(Boolean).join(" "));
  const userTypingRef = useRef(false);

  useEffect(() => {
    if (userTypingRef.current) {
      userTypingRef.current = false;
      return;
    }
    const next = [last, first, middle].filter(Boolean).join(" ");
    setValue(next);
  }, [last, first, middle]);

  return (
    <FormField
      control={control}
      name={lastNameField}
      render={({ field: lastField }) => (
        <FormField
          control={control}
          name={firstNameField}
          render={({ field: firstField }) => (
            <FormField
              control={control}
              name={middleNameField}
              render={({ field: middleField }) => {
                function handleChange(next: string) {
                  userTypingRef.current = true;
                  setValue(next);
                  const parts = next.trim().split(/\s+/);
                  lastField.onChange(parts[0] ?? "");
                  firstField.onChange(parts[1] ?? "");
                  middleField.onChange(parts.slice(2).join(" "));
                }
                function handleClear() {
                  userTypingRef.current = true;
                  setValue("");
                  lastField.onChange("");
                  firstField.onChange("");
                  middleField.onChange("");
                }
                return (
                  <FormItem className="space-y-1.5">
                    <FormLabel className="text-sm font-semibold text-std-primary flex items-center gap-1">
                      ФИО
                      <ChevronRight className="h-4 w-4" />
                    </FormLabel>
                    <FormControl>
                      <div className="relative rounded-xl bg-white px-4 py-3">
                        <Input
                          value={value}
                          onChange={(e) => handleChange(e.target.value)}
                          placeholder="Иванов Иван Иванович"
                          className="border-0 px-0 h-7 text-base shadow-none focus-visible:ring-0 pr-7"
                        />
                        {value && (
                          <button
                            type="button"
                            aria-label="Очистить"
                            onClick={handleClear}
                            className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                );
              }}
            />
          )}
        />
      )}
    />
  );
}
