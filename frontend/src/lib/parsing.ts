// Mirrors core/parsing.py's SUPPORTED_EXTENSIONS exactly.
export const SUPPORTED_EXTENSIONS = [
  ".pdf",
  ".pptx",
  ".docx",
  ".txt",
  ".md",
  ".py",
  ".json",
  ".js",
  ".ts",
  ".tsx",
  ".jsx",
  ".go",
  ".rs",
  ".java",
  ".c",
  ".cpp",
  ".h",
  ".hpp",
  ".html",
  ".css",
  ".yaml",
  ".yml",
  ".toml",
  ".xml",
  ".sql",
  ".sh",
  ".bash",
];

export function hasSupportedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return SUPPORTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}
