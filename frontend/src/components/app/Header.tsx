import { Monitor, Moon, Settings as SettingsIcon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ThemeMode } from "@/hooks/useTheme";

export interface HeaderProps {
  title: string;
  fileCount: number;
  themeMode: ThemeMode;
  onToggleTheme: () => void;
  onOpenSettings: () => void;
}

const THEME_ICON: Record<ThemeMode, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

export function Header({
  title,
  fileCount,
  themeMode,
  onToggleTheme,
  onOpenSettings,
}: HeaderProps) {
  const ThemeIcon = THEME_ICON[themeMode];

  return (
    <header className="flex h-[52px] shrink-0 items-center justify-between bg-card px-4">
      <div className="flex items-center gap-3">
        <h1 className="type-title">{title}</h1>
        {fileCount > 0 && (
          <span className="type-small rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
            {fileCount} {fileCount === 1 ? "file" : "files"}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="pressable hoverable"
          aria-label={`Theme: ${themeMode}. Click to switch.`}
          onClick={onToggleTheme}
        >
          <ThemeIcon size={16} aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="pressable hoverable"
          aria-label="Settings"
          onClick={onOpenSettings}
        >
          <SettingsIcon size={16} aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}
