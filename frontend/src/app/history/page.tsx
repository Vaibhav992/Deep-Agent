import { redirect } from "next/navigation";

// Task history lives in the workspace sidebar (with search); keep old links working.
export default function HistoryPage() {
  redirect("/chat");
}
