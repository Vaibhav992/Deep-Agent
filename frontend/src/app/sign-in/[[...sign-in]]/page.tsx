"use client";

import { SignIn } from "@clerk/nextjs";
import AuthShell from "@/components/auth-shell";

export default function SignInPage() {
  return (
    <AuthShell>
      <SignIn appearance={{ elements: { cardBox: "shadow-none border border-[var(--line)]" } }} />
    </AuthShell>
  );
}
