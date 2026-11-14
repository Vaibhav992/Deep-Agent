"use client";

import { SignUp } from "@clerk/nextjs";
import AuthShell from "@/components/auth-shell";

export default function SignUpPage() {
  return (
    <AuthShell>
      <SignUp appearance={{ elements: { cardBox: "shadow-none border border-[var(--line)]" } }} />
    </AuthShell>
  );
}
