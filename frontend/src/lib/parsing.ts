// Mirrors core/parsing.py's SUPPORTED_EXTENSIONS exactly.
export const SUPPORTED_EXTENSIONS = [
  ".pdf",
  ".pptx",
  ".docx",
  ".txt",
  ".md",
  ".py",
  ".json",
];

export function hasSupportedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return SUPPORTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}
