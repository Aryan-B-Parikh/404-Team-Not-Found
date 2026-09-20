import React from "react";
import { cn } from "../../lib/utils";

export interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  maxWidth?: "default" | "full" | "narrow";
}

export function PageContainer({
  maxWidth = "default",
  className,
  children,
  ...props
}: PageContainerProps) {
  const maxWidthClasses = {
    default: "max-w-[1500px]",
    full: "max-w-full",
    narrow: "max-w-5xl",
  };

  return (
    <div
      className={cn(
        "mx-auto w-full px-3.5 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6",
        maxWidthClasses[maxWidth],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
