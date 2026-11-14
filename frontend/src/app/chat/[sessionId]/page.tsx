"use client";

import { useParams } from "next/navigation";
import Workspace from "@/components/workspace";

export default function TaskPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  return <Workspace sessionId={sessionId} />;
}
