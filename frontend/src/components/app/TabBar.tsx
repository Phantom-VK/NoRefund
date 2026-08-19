import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

export interface TabBarProps<T extends string> {
  tabs: readonly { id: T; label: string; badge?: string | number }[];
  value: T;
  onChange: (id: T) => void;
}

/** Underline tabs on Radix Tabs (roving tabindex, arrow-key nav, correct
 *  ARIA for free) -- parser_view.py and compare_view.py each hand-rolled
 *  this with five cosmetic differences between them. Built once here. */
export function TabBar<T extends string>({ tabs, value, onChange }: TabBarProps<T>) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={(v) => onChange(v as T)}>
      <TabsPrimitive.List className="flex items-center gap-5 border-b border-border">
        {tabs.map((tab) => (
          <TabsPrimitive.Trigger
            key={tab.id}
            value={tab.id}
            className={cn(
              "pressable type-label relative flex items-center gap-1.5 pt-1 pb-2 text-muted-foreground",
              "transition-colors data-[state=active]:text-primary",
              "after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:origin-left after:scale-x-0",
              "after:bg-primary after:transition-transform after:content-['']",
              "data-[state=active]:after:scale-x-100",
            )}
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span className="type-micro rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground">
                {tab.badge}
              </span>
            )}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
    </TabsPrimitive.Root>
  );
}
