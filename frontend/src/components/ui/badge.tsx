import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-pill border px-3 py-0.5 text-label transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-std-primary focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-brand-periwinkle text-white shadow-std-sm hover:bg-brand-periwinkle/85",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow-std-sm hover:bg-destructive/85",
        outline: "border-border-hairline text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
