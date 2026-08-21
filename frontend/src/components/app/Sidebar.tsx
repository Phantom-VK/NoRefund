import { useMemo } from "react";
import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";
import { VIEWS, type ViewId } from "@/lib/views";
import { useBridgeQuery } from "@/hooks/useBridge";
import { bridge } from "@/lib/bridge";

export interface SidebarProps {
  activeView: ViewId;
  onNavigate: (view: ViewId) => void;
}

const SECTIONS = ["Tools", "Data"] as const;

export function Sidebar({ activeView, onNavigate }: SidebarProps) {
  const { data: version } = useBridgeQuery(() => bridge.getAppVersion(), []);
  const sections = useMemo(
    () =>
      SECTIONS.map((section) => ({
        section,
        items: VIEWS.filter((v) => v.section === section),
      })),
    [],
  );

  return (
    <aside className="flex h-full w-[236px] shrink-0 flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-3 px-4 pt-5 pb-4">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-lg font-bold text-primary-foreground">
          $
        </div>
        <div className="min-w-0">
          <p className="type-title truncate">NoRefund</p>
          <p className="type-micro text-muted-foreground">TOKEN &amp; COST ANALYZER</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2">
        {sections.map(({ section, items }) => (
          <div key={section} className="mb-1">
            <p className="type-micro px-2 pt-3 pb-1 text-muted-foreground">{section}</p>
            {items.map((item) => {
              const isActive = item.id === activeView;
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-current={isActive ? "page" : undefined}
                  onClick={() => onNavigate(item.id)}
                  className={cn(
                    "pressable hoverable type-label flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/60",
                  )}
                >
                  <item.icon size={16} aria-hidden="true" />
                  <span className="truncate">{item.navLabel}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="px-3 pb-3">
        <div className="flex items-start gap-2 rounded-md bg-muted px-2.5 py-2">
          <ShieldCheck
            size={14}
            className="mt-0.5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <p className="type-small text-muted-foreground">
            Local analysis. Your files never leave this machine.
          </p>
        </div>
        <p className="type-micro mt-2 text-center text-muted-foreground">
          v{version ?? "…"} · open-source
        </p>
      </div>
    </aside>
  );
}
