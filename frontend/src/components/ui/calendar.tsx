import * as React from "react";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker } from "react-day-picker";
import { ru } from "date-fns/locale";

import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

export function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  captionLayout,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      locale={ru}
      showOutsideDays={showOutsideDays}
      captionLayout={captionLayout}
      className={cn("p-3", className)}
      classNames={{
        root: "rdp",
        months: "flex flex-col sm:flex-row gap-2",
        month: "flex flex-col gap-4",
        month_caption: "flex justify-center pt-1 relative items-center h-9",
        caption_label: "text-sm font-medium inline-flex items-center gap-1",
        dropdowns: "flex items-center gap-2",
        dropdown_root: "relative inline-flex items-center rounded-md border border-input bg-background px-2 py-1 text-sm",
        dropdown:
          "absolute inset-0 z-10 cursor-pointer opacity-0 appearance-none bg-transparent border-0",
        months_dropdown: "",
        years_dropdown: "",
        nav: "absolute inset-x-1 top-1 flex justify-between items-center pointer-events-none",
        button_previous: cn(
          buttonVariants({ variant: "outline" }),
          "size-7 bg-transparent p-0 opacity-50 hover:opacity-100 pointer-events-auto",
        ),
        button_next: cn(
          buttonVariants({ variant: "outline" }),
          "size-7 bg-transparent p-0 opacity-50 hover:opacity-100 pointer-events-auto",
        ),
        chevron: "size-4 fill-current",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "text-muted-foreground rounded-md w-9 font-normal text-[0.8rem]",
        week: "flex w-full mt-2",
        day: cn(
          "relative p-0 text-center text-sm focus-within:relative focus-within:z-20",
          "[&:has([aria-selected])]:bg-std-primary/10",
          "first:[&:has([aria-selected])]:rounded-l-md last:[&:has([aria-selected])]:rounded-r-md",
        ),
        day_button: cn(
          buttonVariants({ variant: "ghost" }),
          "size-9 p-0 font-normal aria-selected:opacity-100",
        ),
        range_start:
          "bg-std-primary text-white [&>button]:bg-std-primary [&>button]:text-white rounded-l-md",
        range_end:
          "bg-std-primary text-white [&>button]:bg-std-primary [&>button]:text-white rounded-r-md",
        range_middle:
          "[&>button]:bg-accent [&>button]:text-accent-foreground",
        selected:
          "[&>button]:bg-std-primary [&>button]:text-white [&>button]:hover:bg-std-primary [&>button]:hover:text-white",
        today: "[&>button]:bg-accent [&>button]:text-accent-foreground",
        outside:
          "text-muted-foreground [&>button]:text-muted-foreground aria-selected:[&>button]:text-muted-foreground",
        disabled: "text-muted-foreground opacity-50",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: (chevronProps) => {
          const { orientation, className: chevClass, ...rest } = chevronProps;
          if (orientation === "left")
            return <ChevronLeft className={cn("size-4", chevClass)} {...rest} />;
          if (orientation === "right")
            return <ChevronRight className={cn("size-4", chevClass)} {...rest} />;
          return <ChevronDown className={cn("size-4", chevClass)} {...rest} />;
        },
      }}
      {...props}
    />
  );
}
