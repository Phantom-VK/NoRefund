import {
  BarChart2,
  Calculator,
  FolderOpen,
  HardDrive,
  Hash,
  Layers,
  type LucideIcon,
} from "lucide-react";

export type ViewId =
  | "calculator"
  | "parser"
  | "compare"
  | "fit_check"
  | "registry"
  | "resources";

export interface ViewMeta {
  id: ViewId;
  title: string;
  navLabel: string;
  icon: LucideIcon;
  section: "Tools" | "Data";
  shortcut: number;
}

// Mirrors gui/main_view.py's _TITLES, nav sections, and shortcut order.
export const VIEWS: readonly ViewMeta[] = [
  {
    id: "calculator",
    title: "Token Calculator",
    navLabel: "Token Calculator",
    icon: Calculator,
    section: "Tools",
    shortcut: 1,
  },
  {
    id: "parser",
    title: "File Parser",
    navLabel: "File Parser",
    icon: FolderOpen,
    section: "Tools",
    shortcut: 2,
  },
  {
    id: "compare",
    title: "Compare Models",
    navLabel: "Compare Models",
    icon: BarChart2,
    section: "Tools",
    shortcut: 3,
  },
  {
    id: "fit_check",
    title: "Self-Host Fit Check",
    navLabel: "Fit Check",
    icon: Hash,
    section: "Tools",
    shortcut: 4,
  },
  {
    id: "registry",
    title: "Model Registry",
    navLabel: "Model Registry",
    icon: Layers,
    section: "Data",
    shortcut: 5,
  },
  {
    id: "resources",
    title: "Resources",
    navLabel: "Resources",
    icon: HardDrive,
    section: "Data",
    shortcut: 6,
  },
];
