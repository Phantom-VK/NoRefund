import { FolderOpen } from "lucide-react";
import { EmptyState } from "@/components/app/EmptyState";

export default function Parser() {
  return (
    <EmptyState
      icon={FolderOpen}
      title="File Parser"
      description="This view is coming in a later phase."
    />
  );
}
